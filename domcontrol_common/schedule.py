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

from . import metrics as mod_metrics


LOGGER = logging.getLogger(__name__)
WEEKDAYS = [
    '%sday' % root
    for root in ('mon', 'tues', 'wednes', 'thurs', 'fri', 'satur', 'sun')
]


class DayRange(object):
    def __init__(self, start='00:00', end='00:00'):
        self.start = self.str_to_int(start)
        self.end = self.str_to_int(end)
        if self.start > self.end:
            raise TypeError('Start must be before end')

    @staticmethod
    def str_to_int(hour_str):
        if isinstance(hour_str, int):
            return hour_str

        hours, mins = hour_str.split(':', 1)
        return int(hours) * 60 + int(mins)

    @staticmethod
    def int_to_str(hour_int):
        hour_int = DayRange.str_to_int(hour_int)
        return '%02d:%02d' % (hour_int / 60, hour_int % 60)

    def __eq__(self, what):
        return self.start == what.start and self.end == what.end

    def __add__(self, what):
        if not isinstance(what, DayRange):
            raise TypeError("Can't sum %s to DayRange" % what.__class__)

        if what.start > self.end:
            return [self, what]
        elif self.start > what.end:
            return [what, self]
        else:
            return [DayRange(
                min(self.start, what.start),
                max(self.end, what.end),
            )]

    def __sub__(self, what):
        if not isinstance(what, DayRange):
            raise TypeError("Can't sum %s to DayRange" % what.__class__)

        if what.start > self.end or self.start > what.end:
            return [DayRange(start=self.start, end=self.end)]
        elif self.start > what.start and self.end < what.end:
            return [DayRange(start=0, end=0)]
        elif self.start < what.start and self.end > what.end:
            return [
                DayRange(start=self.start, end=what.start),
                DayRange(start=what.end, end=self.end),
            ]
        elif self.start < what.start:
            return [DayRange(start=self.start, end=what.start)]
        else:
            return [DayRange(start=what.end, end=self.end)]

    def __contains__(self, what):
        if not isinstance(what, DayRange):
            what = DayRange(start=what, end=what)

        if (
            what.start > self.start
            and what.end < self.end
            and self.end != self.start
        ):
            return True

        return False

    def __repr__(self):
        return 'DayRange(start=%s, end=%s)' % (
            self.int_to_str(self.start),
            self.int_to_str(self.end),
        )

    def __str__(self):
        return repr(self)


    def to_dict(self):
        return {
            'start': self.start,
            'end': self.end,
        }


class DaySchedule(list):
    def add_range(self, day_range):
        self.append(day_range)

    @classmethod
    def from_str(cls, sched_str):
        day_sched = cls()

        for time_range in sched_str.split(','):
            if not time_range:
                continue

            start, end = time_range.split('-', 1)
            day_sched.add_range(DayRange(start=start, end=end))

        return day_sched

    def __repr__(self):
        return 'DaySchedule(%s)' % super(DaySchedule, self).__repr__()

    def __str__(self):
        return repr(self)

    def __contains__(self, what):
        for day_range in self:
            if what in day_range:
                return True

    def to_dict(self):
        return [day_range.to_dict() for day_range in self]


class WeekSchedule(object):
    def __init__(self, name, **kwargs):
        self.name = name

        for key, val in kwargs.items():
            if key not in WEEKDAYS:
                raise TypeError('Parameter %s not allowed' % key)
            setattr(self, key, val)

        for day in WEEKDAYS:
            if not hasattr(self, day):
                setattr(self, day, DaySchedule())

    def schedule_at(self, when):
        return getattr(self, when.strftime('%A').lower())

    def should_trigger(
        self,
        measure,
        metrics,
        action,
        active_limit,
        inactive_limit,
        when=None,
    ):
        when = (
            when
            if when is not None
            else datetime.datetime.now()
        )

        if when.strftime('%H:%S') in self.schedule_at(when):
            limit = active_limit
        else:
            limit = inactive_limit

        if action == 'rise':
            limit = LimitRange(lower=limit)
        elif action == 'lower':
            limit = LimitRange(upper=limit)

        res = None
        for metric in metrics:
            value = getattr(measure, metric).value
            new_res = limit.triggers_at(
                metric_value=value,
                action=action,
            )
            LOGGER.info(
                'Checking %s against %s with action %s, with result %s',
                value,
                limit,
                action,
                new_res
            )
            res = (
                new_res
                if res is None or new_res
                else res
            )

        return res


    def __getitem__(self, key):
        return self.get_limit(key)

    def __repr__(self):
        return (
            ('WeekSchedule(\n  name=%s,\n  ' % self.name)
            + '\n  '.join([
                '%s=%s,' % (day, getattr(self, day))
                for day in WEEKDAYS
            ])
            + '\n)'
        )

    def __str__(self):
        return repr(self)

    def to_dict(self):
        week_sched = {
            'name': self.name,
        }

        for day in WEEKDAYS:
            week_sched[day] = getattr(self, day).to_dict()

        return week_sched


class LimitRange(object):
    def __init__(self, lower=None, upper=None):
        self.lower = lower
        self.upper = upper
        self.dampened_upper = (
            upper * 0.9
            if upper is not None
            else upper
        )
        self.dampened_lower = (
            lower * 1.1
            if lower is not None
            else lower
        )

    def __repr__(self):
        return 'LimitRange(upper=%s, lower=%s)' % (
            self.upper,
            self.lower,
        )

    def __str__(self):
        return repr(self)

    def triggers_at(self, metric_value, action):
        if action == 'rise':
            if self.lower is None:
                return None

            if metric_value < self.lower:
                return True
            # drag a bit deactivating the actors, to avoid flip-flopping
            elif metric_value < self.dampened_lower:
                return None
            else:
                return False

        elif action == 'lower':
            if self.upper is None:
                return None

            if metric_value > self.upper:
                return True
            # drag a bit deactivating the actors, to avoid flip-flopping
            elif metric_value > self.dampened_upper:
                return None
            else:
                return False

        else:
            raise TypeError('Action %s unknow, use "lower" or "rise"' % action)

        return None

    def to_dict(self):
        return {
            'lower': self.lower,
            'upper': self.upper,
        }


def get_schedules(config):
    for section in config.sections():
        if section.split('.', 1)[0] == 'schedule':
            sched_name = section.split('.', 1)[-1]
            days = {}

            for day in WEEKDAYS:
                days[day] = DaySchedule.from_str(config.get(section, day))

            yield WeekSchedule(
                name=sched_name,
                **days
            )

def get_limits(config):
    for section in config.sections():
        if section.split('.', 1)[0] == 'limit':
            sched_name = section.split('.', 1)[-1]
            limits = {}
            for option in config.options(section):
                if option not in mod_metrics.METRICS:
                    continue

                lower, upper = config.get(section, option).split(':', 1)
                limits[option] = LimitRange(
                    upper=upper and float(upper) or None,
                    lower=lower and float(lower) or None,
                )

            yield (sched_name, limits)
