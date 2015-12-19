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
import functools
import json

from flask import (
    Flask,
    request,
)

from domcontrol_common import (
    core,
    conf,
)


app = Flask(__name__)
app_get = functools.partial(app.route, methods=['GET'])
app_post = functools.partial(app.route, methods=['POST'])
json_dumps = functools.partial(json.dumps, sort_keys=True, indent=4)


@app_get('/')
def get():
    status = {
        'config': conf.conf_to_dict(conf.CONFIG),
        'zones': [],
    }

    for zone in core.ZONES.values():
        status['zones'].append(zone.to_dict())

    return json_dumps(status)


@app_get('/<zone>')
@app_get('/<zone>/')
@app_get('/<zone>/<elem_type>')
@app_get('/<zone>/<elem_type>/')
@app_get('/<zone>/<elem_type>/<elem_name>')
@app_get('/<zone>/<elem_type>/<elem_name>/')
@app_get('/<zone>/<elem_type>/<elem_name>/<attr_name>')
def get_elem(zone, elem_type=None, elem_name=None, attr_name=None):
    try:
        zone = core.ZONES[zone]
    except KeyError:
        return (
            'Zone %s not found, available: %s' % (zone, core.ZONES.keys()),
            404
        )

    if elem_type is None:
        return json_dumps(zone.to_dict())

    if elem_type == 'last_measure':
        return json_dumps(zone.last_measure)

    try:
        elems = getattr(zone, elem_type + 's').values()
    except AttributeError:
        return (
            (
                'Zone %s has no element of type %s, available: '
                '[sensor, actor]' % zone.name
            ),
            404
        )

    if elem_name is None:
        return json_dumps([elem.to_dict() for elem in elems])

    try:
        elem = (
            elem for elem in elems if elem.name == elem_name
        ).next()
    except StopIteration:
        return (
            (
                'Zone %s has no %s element named %s, available: %s'
                % (
                    zone.name,
                    elem_type,
                    elem_name,
                    [elem.name for elem in elems]
                )
            ),
            404
        )

    if attr_name is None:
        return json_dumps(elem.to_dict())

    try:
        attr = getattr(elem, attr_name)
    except AttributeError:
        return (
            (
                'Zone %s has no %s element named %s with attribute %s, '
                'available attributes: %s'
                % (zone.name, elem_type, elem_name, attr_name, vars(elem))
            ),
            404
        )

    return json_dumps(attr)


@app_get('/last_measures')
def get_measures():
    measures = {}
    for zone_name, zone in core.ZONES.items():
        measures[zone_name] = zone.last_measure

    return json_dumps(measures)



@app_post('/<zone>/actor/<elem_name>/<attr_name>')
def set_attr(zone, elem_type='actor', elem_name=None, attr_name=None):
    try:
        zone = core.ZONES[zone]
    except KeyError:
        return (
            'Zone %s not found, available: %s' % (zone, core.ZONES.keys()),
            404
        )

    if elem_type is None:
        return json_dumps(zone.to_dict())

    try:
        elems = getattr(zone, elem_type + 's').values()
    except AttributeError:
        return (
            (
                'Zone %s has no element of type %s, available: '
                '[sensor, actor]' % zone.name
            ),
            404
        )

    if elem_name is None:
        return json_dumps([elem.to_json() for elem in elems])

    try:
        elem = (elem for elem in elems if elem.name == elem_name).next()
    except StopIteration:
        return (
            (
                'Zone %s has no %s element named %s, available: %s'
                % (
                    zone.name,
                    elem_type,
                    elem_name,
                    [elem.name for elem in elems],
                )
            ),
            404
        )

    if attr_name is None:
        return json_dumps(elem)

    try:
        attr = getattr(elem, attr_name)
    except AttributeError:
        return (
            (
                'Zone %s has no %s element named %s with attribute %s, '
                'available attributes: %s'
                % (zone.name, elem_type, elem_name, attr_name, vars(elem))
            ),
            404
        )

    if 'value' not in request.form:
        return 'No value parameter passed', 400

    value = json.loads(request.form['value'])
    conf.CONFIG.set(
        '%s.%s' % (elem_type, elem_name),
        attr_name,
        str(value),
    )
    conf.save_config(conf.CONFIG)
    setattr(elem, attr_name, value)
    if elem_type == 'actor' and zone.last_measure:
        zone.check_measure()

    return (
        'Zone %s %s %s, changed %s from %s to %s'
        % (zone.name, elem_type, elem_name, attr_name, attr, value),
        200,
    )
