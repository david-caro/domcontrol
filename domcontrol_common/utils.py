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
import socket
import hashlib


LOGGER = logging.getLogger(__name__)


def format_graphite(measure, prefix=''):
    stats = []
    prefix = prefix and '.' + prefix
    for metric, value, timestamp in measure.to_graphite():
        stats.append(
            'lab.rp1%s.%s %s %s'
            % (prefix, metric, value, timestamp)
        )
        LOGGER.info(
            'lab.rp1%s.%s %s %s'
            % (prefix, metric, value, timestamp)
        )

    return '\n'.join(stats) + '\n'


def send_to_graphite(measure, graphite_url, prefix=''):
    server = graphite_url.split(':', 1)[0]
    port = ':' in graphite_url and int(graphite_url.split(':', 1)[-1]) or 2003
    message = format_graphite(measure, prefix)

    LOGGER.debug('Sending graphite message:\n%s' % message)
    sock = socket.socket()
    try:
        sock.connect((server, port))
        sock.sendall(message)
    except Exception as err:
        LOGGER.error(
            'Got exception %s when trying to send to graphite, continuing...'
            % err
        )

    finally:
        sock.close()


def getfloat(conf, section, option, default=None):
    try:
        return conf.getfloat(section, option)
    except:
        return default


def md5(path):
    with open(path) as fd:
        return hashlib.md5(fd.read()).hexdigest()
