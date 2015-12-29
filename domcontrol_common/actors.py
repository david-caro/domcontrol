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
import logging
import time
import sys
from functools import partial

import RPi.GPIO as GPIO

from . import (
    utils,
)


#: Registry for actor types
ACTORS = {}
LOGGER = logging.getLogger(__name__)


class MetaActor(type):
    def __init__(cls, name, bases, dct):
        if name != 'Actor' and not name.endswith('Mixin'):
            ACTORS[name] = cls


class Actor(object):
    __metaclass__ = MetaActor
    AFFECTED_METRICS = []
    WATCHED_METRICS = []

    def __init__(
        self,
        name,
        action,
        active_time_limit,
        inactive_time_limit,
        schedule,
        zone='default',
        auto_mode=True,
        config=None,
    ):
        self.name = name
        self.zone = zone
        self.auto = auto_mode
        self.schedule = schedule
        self.action = action
        self.active_time_limit = active_time_limit
        self.inactive_time_limit = inactive_time_limit
        self.log_debug('Loaded actor %s', vars(self))

    @property
    def active(self):
        raise NotImplementedError()

    def __nonzero__(self):
        return self.active

    def watches_metrics(self, metrics):
        for metric in metrics:
            if metric in self.WATCHED_METRICS:
                return True

        return False

    def log_info(self, msg, *args):
        LOGGER.info('%s::%s::%s' % (self.zone, self.name, msg), *args)

    def log_debug(self, msg, *args):
        LOGGER.debug('%s::%s::%s' % (self.zone, self.name, msg), *args)

    def activate(self):
        raise NotImplementedError()

    def deactivate(self):
        raise NotImplementedError()

    def parse_measure(self, measure, schedule):
        self.log_debug('Parsing measure %s', measure)
        if not self.auto:
            return

        should_trigger = schedule.should_trigger(
            measure=measure,
            metrics=self.WATCHED_METRICS,
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
            'watches': self.WATCHED_METRICS,
            'affects': self.AFFECTED_METRICS,
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
            'Actor(%s, watches=%s, affects=%s, active=%s, '
            'zone=%s, schedule=%s)'
            % (
                self.name,
                self.WATCHED_METRICS,
                self.AFFECTED_METRICS,
                self.active,
                self.zone,
                self.schedule,
            )
        )

    def __str__(self):
        return self.__repr__()


class RaspberryActorMixin(Actor):
    def __init__(self, config, *args, **kwargs):
        kwargs['config'] = config
        super(RaspberryActorMixin, self).__init__(*args, **kwargs)
        self.pin = int(config('pin'))
        self.setup()

    def get_active(self):
        return bool(GPIO.input(self.pin))

    def set_active(self, value):
        if value:
            self.activate()
        else:
            self.deactivate()

    active = property(get_active, set_active)

    def setup(self):
        self.log_debug('Setting up at pin %s' % self.pin)
        GPIO.setup(
            channel=self.pin,
            direction=GPIO.OUT,
            initial=GPIO.LOW,
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


class HumidityActor(RaspberryActorMixin):
    WATCHED_METRICS = ['humidity']
    AFFECTED_METRICS = ['humidity']


class TemperatureActor(RaspberryActorMixin):
    WATCHED_METRICS = ['temperature']
    AFFECTED_METRICS = ['temperature']


class PresenceLightActor(RaspberryActorMixin):
    WATCHED_METRICS = ['luminosity', 'presence']
    AFFECTED_METRICS = ['luminosity']

    def parse_measure(self, measure, schedule):
        self.log_debug('Parsing measure %s', measure)
        if not self.auto:
            return

        should_trigger = schedule.should_trigger(
            measure=measure,
            metrics=self.AFFECTED_METRICS,
            action=self.action,
            active_limit=self.active_time_limit and sys.maxint,
            inactive_limit=self.inactive_time_limit and sys.maxint,
        )


        if (
            should_trigger is None
            or measure.presence.value is None
        ):
            self.log_debug(
                'Skipping any changes, should_trigger=%s', should_trigger)
            return
        elif (
            should_trigger
            and (
                measure.luminosity.value is None
                or int(time.time()) - measure.presence.value < 250
            )
        ):
            self.log_debug(
                'Activating, should_trigger=%s, last presence: %s, time: %s',
                should_trigger,
                measure.presence.value,
                int(time.time())
            )
            self.activate()
        else:
            self.log_debug(
                'Deactivating, should_trigger=%s, last presence: %s, time: %s',
                should_trigger,
                measure.presence.value,
                int(time.time())
            )
            self.deactivate()



def get_actors(config):
    for section in config.sections():
        if section.split('.', 1)[0] == 'actor':
            actor_class = config.get(section, 'type')
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
            if actor_class in ACTORS:
                yield ACTORS[actor_class](
                    config=partial(config.get, section),
                    name=actor_name,
                    action=actor_action,
                    zone=actor_zone,
                    schedule=actor_schedule,
                    active_time_limit=actor_active_time_limit,
                    inactive_time_limit=actor_inactive_time_limit,
                )


