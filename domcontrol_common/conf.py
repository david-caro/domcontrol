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
import os

from . import utils


LOGGER = logging.getLogger(__name__)
DEFAULT_CONF = os.path.expanduser('~/.domcontrol.conf')

#: Default config
CONF_DEFAULTS = {
    'pin_numbering': 'BCM',
    'loop_sleep_time': '10',
    'graphite_url': '',
    'zone': 'default',
    'schedule': 'default',
}
DEFAULT_SCHEDULE = {
    'monday': '08:00-13:00, 15:00-20:00',
    'tuesday': '08:00-13:00, 15:00-20:00',
    'wednesday': '08:00-13:00, 15:00-20:00',
    'thursday': '08:00-13:00, 15:00-20:00',
    'friday': '08:00-13:00, 15:00-20:00',
    'saturday': '08:00-13:00, 15:00-20:00',
    'sunday': '08:00-13:00, 15:00-20:00',
}
CONFIG = None


def conf_to_dict(config):
    conf = {}
    for section in config.sections():
        conf[section] = {}
        for option in config.options(section):
            conf[section][option] = config.get(section, option)

    return conf


def load_config(conf_file, defaults):
    config = ConfigParser.SafeConfigParser(
        defaults=defaults,
    )

    if not conf_file:
        if os.path.exists(DEFAULT_CONF):
            conf_file = DEFAULT_CONF
        else:
            LOGGER.info('Conf file %s not found', DEFAULT_CONF)

    if not conf_file:
        raise RuntimeError('No config file found!')

    LOGGER.info('Loading config %s', conf_file)
    if conf_file:
        config.read(conf_file)
        config.loaded_file = conf_file
        config.loaded_file_sum = utils.md5(conf_file)

    if not config.has_section('schedule.default'):
        config.add_section('schedule.default')
        for option, value in DEFAULT_SCHEDULE.items():
            config.set('schedule.default', option, value)

    return config


def reload_config():
    if not CONFIG:
        raise RuntimeError(
            'Can\'t reload any config, it has not been  loaded yet'
        )

    new_sum = utils.md5(CONFIG.loaded_file)
    if new_sum == CONFIG.loaded_file_sum:
        LOGGER.debug('No changes to config')
        return

    config = ConfigParser.SafeConfigParser(
        defaults=CONF_DEFAULTS,
    )
    conf_file = CONFIG.loaded_file
    LOGGER.info('Loading config %s', conf_file)
    if conf_file:
        config.read(conf_file)
        config.loaded_file = conf_file
        config.loaded_file_sum = utils.md5(conf_file)

    return config


def save_config(config):
    with open(config.loaded_file, 'w') as conf_fd:
        config.write(conf_fd)

    config.loaded_file_sum = utils.md5(config.loaded_file)
