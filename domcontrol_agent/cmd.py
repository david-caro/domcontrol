#!/usr/bin/env python
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
import argparse
import logging
import sys
import threading

from domcontrol_common import (
    core,
    conf,
)

from . import web


LOGGER = logging.getLogger('cli')


def main(args=None):
    logging.basicConfig(level=logging.INFO)

    if not args:
        args = sys.argv[0:]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config',
        default=None
    )
    parser.add_argument(
        '--host',
        action='store',
        default='127.0.0.1'
    )
    parser.add_argument(
        '-p', '--port',
        action='store',
        default='5000'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
    )
    args = parser.parse_args()

    if args.verbose:
        logging.root.setLevel(
            logging.DEBUG,
        )
        logging.root.handlers[0].formatter._fmt = (
            '%(asctime)s::%(levelname)s::'
            '%(name)s.%(funcName)s:%(lineno)d::'
            '%(message)s'
        )

    conf.CONFIG = conf.load_config(
        args.config,
        defaults=conf.CONF_DEFAULTS,
    )
    core.setup(conf.CONFIG)

    controller = threading.Thread(
        target=core.main_loop,
        args=[conf.CONFIG]
    )

    try:
        LOGGER.info('Starting controller')
        controller.start()
        LOGGER.info('Starting web server')
        web.app.run(host=args.host, port=args.port)
    except:
        core.STOP.set()
        core.cleanup()
        raise


if __name__ == '__main__':
    main(sys.argv[1:])
