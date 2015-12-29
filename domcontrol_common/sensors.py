# encoding:utf-8
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
import ConfigParser
import logging
import time
import threading
from functools import partial

import Adafruit_DHT
import RPi.GPIO as GPIO

from . import (
    metrics as mod_metrics,
    utils,
)


#: Registry for sensor types
SENSORS = {}
LOGGER = logging.getLogger(__name__)


class MetaSensor(type):
    def __init__(cls, name, bases, dct):
        if name != 'Sensor' and not name.endswith('Mixin'):
            SENSORS[name] = cls


class Sensor(object):
    __metaclass__ = MetaSensor
    METRICS = []

    def __init__(
        self,
        name,
        pin,
        config=None,
        graphite_url=None,
        zone='default',
    ):
        self.name = name
        self.pin = int(pin)
        self.graphite_url = graphite_url
        self.zone = zone
        self.last_measure = None
        self.log_debug('Initializing')

        for metric in self.METRICS:
            if metric not in mod_metrics.METRICS:
                raise TypeError('Unknown metric %s' % metric)

        self.log_debug('Loaded Sensor %s', vars(self))

    def log_info(self, msg, *args):
        LOGGER.info('%s::%s::%s' % (self.zone, self.name, msg), *args)

    def log_debug(self, msg, *args):
        LOGGER.debug('%s::%s::%s' % (self.zone, self.name, msg), *args)

    def add_callback(self, func):
        pass

    def read(self):
        raise NotImplementedError()

    def to_dict(self):
        return {
            'name': self.name,
            'pin': self.pin,
            'last_measure': self.last_measure and self.last_measure.to_dict(),
            'zone': self.zone,
        }

    def __repr__(self):
        return (
            'Sensor(%s, pin=%d)'
            % (
                self.name,
                self.pin,
            )
        )

    def __str__(self):
        return self.__repr__()


class RaspberrySensorMixin(Sensor):
    def __init__(self, *args, **kwargs):
        super(RaspberrySensorMixin, self).__init__(*args, **kwargs)
        self.setup()

    def setup(self, **kwargs):
        self.log_debug('Setting up on pin %s: %s', self.pin, kwargs)
        GPIO.setup(
            channel=self.pin,
            direction=GPIO.IN,
            **kwargs
        )


class EventRaspberrySensorMixin(RaspberrySensorMixin):
    EVENT = GPIO.RISING
    LOCK = threading.Lock()

    def __init__(self, *args, **kwargs):
        super(EventRaspberrySensorMixin, self).__init__(*args, **kwargs)
        self.callbacks = []
        GPIO.add_event_detect(
            self.pin,
            self.EVENT,
            bouncetime=1000,
        )
        GPIO.add_event_callback(
            self.pin,
            self.event_happened,
        )
        self.log_debug('Initialized event sensor')

    def add_callback(self, func):
        self.log_debug('Adding callback %s', func)
        self.callbacks.append(func)

    def event_happened(self, pin):
        if self.LOCK.locked():
            self.log_debug('\n    EVENT-- ignoring, already parsing event')
            return

        self.LOCK.acquire()
        try:
            if pin != self.pin:
                self.log_debug('\n    EVENT-- ignoring, wrong channel %s' % pin)
                return

            self.log_debug('\n    EVENT-- Event detected on channel %s' % pin)
            measure = {}
            for metric in self.METRICS:
                measure[metric] = int(time.time())

            self.last_measure = mod_metrics.Measure(**measure)

            for callback in self.callbacks:
                callback(
                    measure=self.last_measure,
                    sensor=self.name,
                    metrics=self.METRICS,
                )
        finally:
            self.LOCK.release()

    def read(self):
        self.log_debug('value=%s' % self.last_measure)
        return self.last_measure


class LightSensor(RaspberrySensorMixin):
    METRICS = [
        'luminosity'
    ]

    def read(self):
        value = GPIO.input(self.pin) and 1 or 0
        self.last_measure = mod_metrics.Measure(
            luminosity=value
        )
        self.log_debug('value=%s' % self.last_measure)
        return self.last_measure


class PresenceSensor(EventRaspberrySensorMixin):
    METRICS = [
        'presence'
    ]
    EVENT = GPIO.FALLING


class DHTSensor(RaspberrySensorMixin):
    #: Match between config sensor type option and the lib  type
    DHT_SENSOR_TYPES = {
        '11': Adafruit_DHT.DHT11,
        '22': Adafruit_DHT.DHT22,
        '2302': Adafruit_DHT.AM2302,
    }
    METRICS = [
        'temperature',
        'humidity'
    ]

    def __init__(self, config, *args, **kwargs):
        kwargs['config'] = config
        super(DHTSensor, self).__init__(*args, **kwargs)
        dht_type = config(option='dht_type')
        self.dht_type = self.DHT_SENSOR_TYPES[dht_type]
        for metric in self.METRICS:
            try:
                offset = float(config(option=metric + '_offset'))
            except ConfigParser.NoOptionError:
                offset = None

            setattr(self, metric + '_offset', offset)

    def read(self):
        """
        Gets a valid read measure (right now it has to retry a few times, read a
        couple values and returns the max as there are low value outliers)

        Very dependent on the hardware

        Returns:
            Measure: timestamp, temperature and humidity reads
        """
        self.log_debug('Reading metrics')
        humidity = None
        prev_hum = None
        temperature = None
        prev_temp = None

        while humidity is None:
            self.log_debug(
                'Doing a read loop, prev_hum=%s, humidity=%s'
                % (prev_hum, humidity)
            )
            if prev_hum is None:
                prev_hum, prev_temp = Adafruit_DHT.read_retry(
                    self.dht_type,
                    self.pin,
                )
            else:
                humidity, temperature = Adafruit_DHT.read_retry(
                    self.dht_type,
                    self.pin,
                )
            time.sleep(1)

        norm_temp = (
            self.temperature_offset + max((temperature, prev_temp))
            if self.temperature_offset is not None
            else max((temperature, prev_temp))
        )
        norm_hum = (
            self.humidity_offset + max((humidity, prev_hum))
            if self.humidity_offset is not None
            else max((humidity, prev_hum))
        )

        self.last_measure = mod_metrics.Measure(
            temperature=norm_temp,
            humidity=norm_hum,
        )

        if self.graphite_url:
            utils.send_to_graphite(
                measure=self.last_measure,
                graphite_url=self.graphite_url,
                prefix=self.name,
            )

        return self.last_measure


def get_sensors(config):
    graphite_url = config.get('general', 'graphite_url')
    for section in config.sections():
        if section.split('.', 1)[0] == 'sensor':
            sensor_type = config.get(section, 'type')
            sensor_pin = config.get(section, 'pin')
            sensor_name = section.split('.', 1)[-1]
            sensor_zone = config.get(section, 'zone')

            try:
                yield SENSORS[sensor_type](
                    config=partial(config.get, section=section),
                    name=sensor_name,
                    pin=sensor_pin,
                    graphite_url=graphite_url,
                    zone=sensor_zone,
                )
            except KeyError:
                raise KeyError(
                    'Sensor of type %s not found, availabe ones: %s'
                    % (sensor_type, SENSORS.keys())
                )
