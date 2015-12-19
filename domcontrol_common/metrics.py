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
import time


METRICS = {}


class MetaMetric(type):
    def __init__(cls, name, bases, dct):
        if name != 'Metric':
            METRICS[name.lower()] = cls


class Metric(object):
    __metaclass__ = MetaMetric

    def __init__(self, value):
        self.value = value

    def to_dict(self):
        return self.value

    def __str__(self):
        return repr(self)


class Temperature(Metric):
    def __init__(self, value):
        value = float(value)
        if value < -273.15:
            raise TypeError('Temperature can\'t be lower than -273.15°C')

        super(Temperature, self).__init__(value)

    def __repr__(self):
        return (
            '%.2f°C' % self.value
            if self.value is not None
            else u'None'
        )


class Humidity(Metric):
    def __init__(self, value):
        value = float(value)
        if value > 100:
            raise TypeError('Humidity can\'t be higher than 100')
        if value < 0:
            raise TypeError('Humidity can\'t be lower than 0')

        super(Humidity, self).__init__(value)

    def __repr__(self):
        return (
            '%.2f%%' % self.value
            if self.value is not None
            else 'None'
        )


class Timestamp(Metric):
    def __init__(self, value=None):
        value = value is None and int(time.time()) or int(value)
        if value < 0:
            raise TypeError('Invalid timestamp %s' % value)

        super(Timestamp, self).__init__(value)

    def __repr__(self):
        return datetime.datetime.fromtimestamp(
                int(self.value)
            ).strftime('%H:%M:%S')


class Measure(object):
    def __init__(self, timestamp=None, **kwargs):
        self.timestamp = Timestamp(timestamp)
        self.metrics = METRICS.keys()
        for metric, metric_cls in METRICS.items():
            if metric in kwargs:
                value = kwargs.pop(metric)
            else:
                value = None
            setattr(self, metric.lower(), metric_cls(value))

        if kwargs:
            raise TypeError('Unknown metrics %s' % kwargs.keys())

    def to_dict(self):
        measure = {
        }
        for metric in self.metrics:
            measure[metric] = getattr(self, metric).to_dict()

        return measure

    def __repr__(self):
        mystr = 'Measure(timestamp=%s, %s)' % (
            self.timestamp,
            ', '.join([
                '%s=%s' % (metric, getattr(self, metric))
                for metric in self.metrics
            ])
        )

        return mystr


def get_mean_measure(measures):
    if not measures:
        return None

    final_metrics = {}
    timestamp = str(int(time.time()))
    for index, measure in enumerate(measures):
        for metric in METRICS.keys():
            if metric.lower() == 'timestamp':
                continue
            if metric in final_metrics and final_metrics[metric] is not None:
                final_metrics[metric] = (
                    final_metrics[metric] * index
                    + getattr(measure, metric).value
                ) / (index + 1)
            else:
                final_metrics[metric] = getattr(measure, metric).value

        timestamp = measure.timestamp.value

    return Measure(timestamp=timestamp, **final_metrics)

