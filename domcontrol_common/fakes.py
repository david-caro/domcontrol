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
from logging import getLogger
from random import randint


LOGGER = getLogger(__name__)


class DummyGPIO(object):
    IN = 1
    OUT = 0

    @property
    def BCM(self):
        val = bool(randint(0, 1))
        LOGGER.debug(
            'DummyGPIO%s: BCM got called with result %s' % (self, val)
        )
        return val

    @property
    def FALLING(self):
        val = bool(randint(0, 1))
        LOGGER.debug(
            'DummyGPIO%s: FALLING got called with result %s' % (self, val)
        )
        return val

    @property
    def LOW(self):
        val = bool(randint(0, 1))
        LOGGER.debug(
            'DummyGPIO%s: LOW got called with result %s' % (self, val)
        )
        return val

    @property
    def RISING(self):
        val = bool(randint(0, 1))
        LOGGER.debug(
            'DummyGPIO%s: RISING got called with result %s' % (self, val)
        )
        return val

    @property
    def BOTH(self):
        val = bool(randint(0, 1))
        LOGGER.debug(
            'DummyGPIO%s: BOTH got called with result %s' % (self, val)
        )
        return val

    @staticmethod
    def setup(*args, **kwargs):
        LOGGER.debug(
            'DummyGPIO: setup got called with args %s and kwargs %s' % (
                args,
                kwargs,
            )
        )

    @staticmethod
    def input(pin):
        LOGGER.debug('DummyGPIO: input got called with pin %s' % pin)
        return randint(0, 255)

    @staticmethod
    def output(pin, value):
        LOGGER.debug(
            'DummyGPIO: output got called with pin %s and value %s'
            % (pin, value)
        )

    @staticmethod
    def setwarnings(value=False):
        LOGGER.debug(
            'DummyGPIO: setwarnings got called with value %s' % value
        )

    @staticmethod
    def setmode(pin_numbering):
        LOGGER.debug(
            'DummyGPIO: setmode got called with pin_numbering %s'
            % pin_numbering
        )

    @staticmethod
    def cleanup():
        LOGGER.debug('DummyGPIO: cleanup got called.')

    @staticmethod
    def add_event_detect(pin, event, bouncetime):
        LOGGER.debug(
            'DummyGPIO: add_event_detect got called with pin %s, event %s, '
            'bouncetime %s'
            % (
                pin,
                event,
                bouncetime,
            )
        )

    @staticmethod
    def add_event_callback(pin, event_happened):
        LOGGER.debug(
            'DummyGPIO: add_event_detect got called with pin %s, '
            'event_happened %s'
            % (
                pin,
                event_happened,
            )
        )


class DummyAdafruit_DHT(object):
    @property
    def DHT11(self):
        LOGGER.debug(
            'DummyAdafruit_DHT%s: DHT11 got called' % self
        )
        return 1

    @property
    def DHT22(self):
        LOGGER.debug(
            'DummyAdafruit_DHT%s: DHT22 got called' % self
        )
        return 1

    @property
    def AM2302(self):
        LOGGER.debug(
            'DummyAdafruit_DHT%s: AM2302 got called' % self
        )
        return 1

    @staticmethod
    def read_retry(dht_type, pin):
        humidity = randint(0, 100)
        temperature = randint(-50, 50)
        LOGGER.debug(
            'DummyAdafruit_DHT: read_retry got called with dht_type %s and '
            'pin %s, will return humidity %s and temperature %s.' % (
                dht_type,
                pin,
                humidity,
                temperature,
            )
        )
        return humidity, temperature
