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
import datetime
import logging
import time


LOGGER = logging.getLogger(__name__)
METRICS = {}


class MetaMetric(type):
    def __init__(cls, name, bases, dct):
        if name != 'Metric':
            METRICS[name.lower()] = cls


class Metric(object):
    __metaclass__ = MetaMetric
    max_value = None
    min_value = None
    val_type = str

    def __init__(self, value):
        self.value = (
            self.val_type(value)
            if value is not None
            else value
        )
        self.check_value()

    def to_dict(self):
        return self.value

    def check_value(self):
        if self.value is None:
            return

        if self.max_value is not None and self.value > self.max_value:
            raise TypeError(
                '%s can\'t higher than max %s'
                % (
                    self,
                    self.max_value
                )
            )
        if self.min_value is not None and self.value < self.min_value:
            raise TypeError(
                '%s can\'t be lower than min %s'
                % (
                    self,
                    self.min_value
                )
            )

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return (
            '%s' % self.value
            if self.value is not None
            else u'None'
        )


class Temperature(Metric):
    val_type = float
    min_value = -273.15

    def __repr__(self):
        return (
            '%.2f°C' % self.value
            if self.value is not None
            else u'None'
        )


class Humidity(Metric):
    val_type = float
    max_value = 100
    min_value = 0

    def __repr__(self):
        return (
            '%.2f%%' % self.value
            if self.value is not None
            else 'None'
        )


class Luminosity(Metric):
    max_value = 1
    min_value = 0
    val_type = int


class Presence(Metric):
    min_value = 0
    val_type = int

    def __init__(self, value=None):
        LOGGER.debug('Presence %s' % value)
        value = (
            None
            if value is None
            else int(value)
        )
        super(Presence, self).__init__(value)

    def __repr__(self):
        return (
            datetime.datetime.fromtimestamp(
                int(self.value)
            ).strftime('%H:%M:%S')
            if self.value is not None
            else 'None'
        )


class Timestamp(Metric):
    val_type = int
    min_value = 0

    def __init__(self, value=None):
        LOGGER.debug('Timestamp %s' % value)
        value = value is None and int(time.time()) or int(value)
        super(Timestamp, self).__init__(value)

    def __repr__(self):
        return datetime.datetime.fromtimestamp(
                int(self.value)
            ).strftime('%H:%M:%S')


class Measure(object):
    def __init__(self, timestamp=None, **kwargs):
        LOGGER.debug('::__init__::Measure, ts=%s, %s' % (timestamp, kwargs))
        self.timestamp = Timestamp(timestamp)
        self.metrics = METRICS.keys()
        for metric, metric_cls in METRICS.items():
            LOGGER.debug('::__init__:: adding metric %s::%s', metric, metric_cls)
            if metric in kwargs:
                value = kwargs.pop(metric)
            elif metric == 'timestamp':
                continue
            else:
                value = None
            setattr(self, metric.lower(), metric_cls(value))

        if kwargs:
            raise TypeError('Unknown metrics %s' % kwargs.keys())

    def get_valued_metrics(self):
        return [
            metric
            for metric in self.metrics
            if getattr(self, metric) is not None
        ]

    def to_dict(self):
        measure = {
        }
        for metric in self.metrics:
            measure[metric] = getattr(self, metric).to_dict()

        return measure

    def __repr__(self):
        mystr = 'Measure(%s)' % (
            ', '.join([
                '%s=%s' % (metric, getattr(self, metric))
                for metric in self.metrics
            ])
        )

        return mystr

    def to_graphite(self):
        LOGGER.debug('Measure::Sending to graphite %s', self)
        for metric in self.metrics:
            value = getattr(self, metric).value
            if value is None:
                LOGGER.debug('Skipping metric %s with value %s', metric, value)
                continue

            if metric == 'presence':
                LOGGER.debug(
                    'Got presence, with age %s', self.timestamp.value - value
                )
                if self.timestamp.value - value < 60:
                    value = 1
                else:
                    value = 0

            LOGGER.debug('Finally got %s, %s', metric, value)
            yield (metric, value, self.timestamp.value)


def get_mean_measure(measures):
    if not measures:
        return None

    metrics = {}

    for measure in measures:
        if measure is None:
            continue

        for metric in measure.metrics:
            value = getattr(measure, metric).value
            if (
                metric.lower() == 'timestamp'
                or value is None
            ):
                continue

            if metric not in metrics:
                metrics[metric] = []

            metrics[metric].append(value)

    final_metrics = {}
    timestamp = str(int(time.time()))
    for metric, values in metrics.items():
        if metric in ('luminosity', 'presence'):
            final_metrics[metric] = max(values)
            continue

        final_metrics[metric] = sum(values) / len(values)

    return Measure(timestamp=timestamp, **final_metrics)

