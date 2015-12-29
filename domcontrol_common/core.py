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
    actors as mod_actors,
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
        self.measures = {}

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

    def check_measure(self, measure=None, sensor=None, metrics=None):
        if not self.last_measure and not measure:
            return
        elif not measure:
            measure = self.last_measure
        elif not self.last_measure:
            measure = measure
        else:
            measure = mod_metrics.get_mean_measure([
                measure,
                self.last_measure,
            ])

        if sensor:
            self.measures[sensor] = measure

        logging.debug('zone.%s::Checking measure %s', self.name, measure)

        logging.info(
            'zone.%s::Checking if any actor has to act on it',
            self.name,
        )
        if metrics:
            logging.info(
                'zone.%s::   filtering by metrics %s',
                self.name,
                metrics
            )
        for actor in self.actors.values():
            logging.debug('  Checking %s', actor.name)
            if not metrics or actor.watches_metrics(metrics):
                actor.parse_measure(
                    measure=measure,
                    schedule=self.schedules[actor.schedule]
                )

    def get_measure(self):
        for sensor_name, sensor in self.sensors.items():
            if STOP.is_set():
                raise RuntimeError('Stopping')

            self.measures[sensor_name] = sensor.read()

        return mod_metrics.get_mean_measure(self.measures.values())

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


def load_zones(config):
    zones = {}
    sensors = list(mod_sensors.get_sensors(config))
    actors = list(mod_actors.get_actors(config))
    schedules = list(mod_schedule.get_schedules(config))

    for sensor in sensors:
        if sensor.zone not in zones:
            zones[sensor.zone] = Zone(sensor.zone)

        zones[sensor.zone].add_sensor(sensor)

        sensor.add_callback(zones[sensor.zone].check_measure)

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
        for _ in range(100):
            time.sleep(
                float(config.getint('general', 'loop_sleep_time'))/100
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
    GPIO.setwarnings(False)
    GPIO.cleanup()
    time.sleep(1)
    GPIO.cleanup()


def cleanup():
    GPIO.cleanup()
