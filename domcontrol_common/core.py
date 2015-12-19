# This file is part of domcontrol.
#
# domcontrol is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# domcontrol is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with domcontrol.  If not, see <http://www.gnu.org/licenses/>.
#
import time
import logging
import threading

import RPi.GPIO as GPIO

from . import (
    utils,
    sensors as mod_sensors,
    metrics as mod_metrics,
    schedule as mod_schedule,
    conf as mod_conf,
)


LOGGER = logging.getLogger(__name__)
ZONES = {}
STOP = threading.Event()


class Zone(object):
    def __init__(self, name):
        self.name = name
        self.actors = {}
        self.sensors = {}
        self.last_measure = None
        self.schedules = {}

    def add_actor(self, actor):
        self.actors[actor.name] = actor

    def add_sensor(self, sensor):
        self.sensors[sensor.name] = sensor

    def add_schedule(self, schedule):
        self.schedules[schedule.name] = schedule


    def do_measure(self):
        logging.info('zone.%s::Doing next measure', self.name)
        self.last_measure = self.get_measure()

        logging.info('zone.%s::Got measure %s', self.name, self.last_measure)
        self.check_measure()

    def check_measure(self):
        if not self.last_measure:
            return

        logging.info(
            'zone.%s::Checking if any actor has to act on it',
            self.name,
        )
        for actor in self.actors.values():
            actor.parse_measure(
                measure=self.last_measure,
                schedule=self.schedules[actor.schedule]
            )

    def get_measure(self):
        return get_measure(self.sensors.values())

    def to_dict(self):
        zone = {
            'name': self.name,
            'actors': [],
            'sensors': [],
            'last_measure': self.last_measure and self.last_measure.to_dict(),
            'schedules': [],
        }

        for actor in self.actors.values():
            zone['actors'].append(actor.to_dict())

        for sensor in self.sensors.values():
            zone['sensors'].append(sensor.to_dict())

        for schedule in self.schedules.values():
            zone['schedules'].append(schedule.to_dict())

        return zone


class Actor(object):
    def __init__(
        self,
        name,
        type,
        pin,
        action,
        active_time_limit,
        inactive_time_limit,
        schedule,
        zone='default',
        auto_mode=True,
    ):
        self.name = name
        self.type = type
        self.pin = int(pin)
        self.zone = zone
        self.auto = auto_mode
        self.schedule = schedule
        self.action = action
        self.active_time_limit = active_time_limit
        self.inactive_time_limit = inactive_time_limit
        self.setup()

    def get_active(self):
        return bool(GPIO.input(self.pin))

    def set_active(self, value):
        if value:
            self.activate()
        else:
            self.deactivate()

    active = property(get_active, set_active)

    def __nonzero__(self):
        return self.active

    def log_info(self, msg, *args):
        LOGGER.info('%s::%s::%s' % (self.zone, self.name, msg), *args)

    def log_debug(self, msg, *args):
        LOGGER.debug('%s::%s::%s' % (self.zone, self.name, msg), *args)

    def setup(self):
        self.log_debug('Setting up')
        GPIO.setup(
            channel=self.pin,
            direction=GPIO.OUT,
        )

    def activate(self):
        if not self.active:
            self.log_info('Activated')
            GPIO.output(
                self.pin,
                GPIO.HIGH,
            )
        else:
            self.log_info('Already active')

    def deactivate(self):
        if self.active:
            self.log_info('Deactivating')
            GPIO.output(
                self.pin,
                GPIO.LOW,
            )
        else:
            self.log_info('Already inactive')

    def cleanup(self):
        GPIO.cleanup(channel=self.pin)

    def parse_measure(self, measure, schedule):
        if not self.auto:
            return

        should_trigger = schedule.should_trigger(
            measure=measure,
            metric=self.type,
            action=self.action,
            active_limit=self.active_time_limit,
            inactive_limit=self.inactive_time_limit,
        )

        if should_trigger is None:
            return
        elif should_trigger:
            self.activate()
        else:
            self.deactivate()

    def to_dict(self):
        return {
            'name': self.name,
            'pin': self.pin,
            'type': self.type,
            'zone': self.zone,
            'auto': self.auto,
            'action': self.action,
            'schedule': self.schedule,
            'active': self.active,
            'active_time_limit': self.active_time_limit,
            'inactive_time_limit': self.inactive_time_limit,
        }

    def __repr__(self):
        return (
            'Actor(%s, pin=%d, type=%s, active=%s, '
            'zone=%s, schedule=%s)'
            % (
                self.name,
                self.pin,
                self.type,
                self.active,
                self.zone,
                self.schedule,
            )
        )

    def __str__(self):
        return self.__repr__()


def get_actors(config):
    for section in config.sections():
        if section.split('.', 1)[0] == 'actor':
            actor_type = config.get(section, 'type')
            actor_pin = config.get(section, 'pin')
            actor_name = section.split('.', 1)[-1]
            actor_action = config.get(section, 'action')
            actor_zone = config.get(section, 'zone')
            actor_schedule = config.get(section, 'schedule')
            actor_active_time_limit = utils.getfloat(
                config,
                section,
                'active_time_limit'
            )
            actor_inactive_time_limit = utils.getfloat(
                config,
                section,
                'inactive_time_limit'
            )
            if actor_pin:
                yield Actor(
                    name=actor_name,
                    pin=actor_pin,
                    type=actor_type,
                    action=actor_action,
                    zone=actor_zone,
                    schedule=actor_schedule,
                    active_time_limit=actor_active_time_limit,
                    inactive_time_limit=actor_inactive_time_limit,
                )


def get_measure(sensors):
    measures = []
    for sensor in sensors:
        if STOP.is_set():
            raise RuntimeError('Stopping')

        measures.append(sensor.read())

    return mod_metrics.get_mean_measure(measures)


def load_zones(config):
    zones = {}
    sensors = list(mod_sensors.get_sensors(config))
    actors = list(get_actors(config))
    schedules = list(mod_schedule.get_schedules(config))

    for sensor in sensors:
        if sensor.zone not in zones:
            zones[sensor.zone] = Zone(sensor.zone)

        zones[sensor.zone].add_sensor(sensor)

    for actor in actors:
        if actor.zone not in zones:
            zones[actor.zone] = Zone(actor.zone)

        zones[actor.zone].add_actor(actor)

    for schedule in schedules:
        for zone in zones.values():
            zone.add_schedule(schedule)

    return zones


def main_loop(config):
    global ZONES
    global LAST_MEASURES

    graphite_url = config.get('general', 'graphite_url')

    ZONES = load_zones(config)

    while not STOP.is_set():
        changed_config = mod_conf.reload_config()
        if changed_config:
            mod_conf.CONFIG = changed_config
            ZONES = load_zones(mod_conf.CONFIG)

        for zone in ZONES.values():
            zone.do_measure()

            if zone.last_measure:
                if graphite_url:
                    utils.send_to_graphite(
                        measure=zone.last_measure,
                        graphite_url=graphite_url,
                    )

        if STOP.is_set():
            return

        # busy sleep
        for _ in range(10):
            time.sleep(
                float(config.getint('general', 'loop_sleep_time'))/10
            )
            if STOP.is_set():
                return


def setup(config):
    pin_numbering = config.get('general', 'pin_numbering')
    try:
        pin_numbering = getattr(GPIO, pin_numbering)
    except:
        LOGGER.error('Numbering %s not supported', pin_numbering)
        raise

    GPIO.setwarnings(False)
    GPIO.setmode(pin_numbering)
