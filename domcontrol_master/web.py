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
import functools
import json
import os
import logging

import requests
from flask import (
    Flask,
    render_template,
    request,
    redirect,
)

from flask.ext.bootstrap import Bootstrap
from domcontrol_common import (
    conf,
    metrics as mod_metrics,
)


app = Flask(__name__)
Bootstrap(app)

app_get = functools.partial(app.route, methods=['GET'])
app_post = functools.partial(app.route, methods=['POST'])
json_dumps = functools.partial(json.dumps, sort_keys=True, indent=4)

LOGGER = logging.getLogger(__name__)


class Agent(object):

    def __init__(self, name, url):
        self.config = {}
        self.zones = {}
        self.url = url
        self.name = name

        self.load_json(requests.get(url).json())

    def load_json(self, agent_data):
        self.zones = agent_data['zones']

        zone_confs = [
            section
            for section in conf.CONFIG.sections()
            if section.startswith('zone.')
        ]

        for zone in self.zones:
            if 'zone.' + zone['name'] in zone_confs:
                zone['graph_url'] = conf.CONFIG.get(
                    'zone.' + zone['name'],
                    'graph_url'
                )

            if zone['last_measure']:
                zone['last_measure'] = \
                    mod_metrics.Measure(**zone['last_measure'])

            for sensor in zone['sensors']:
                if sensor['last_measure']:
                    sensor['last_measure'] = \
                        mod_metrics.Measure(**sensor['last_measure'])

        self.config = agent_data['config']


def get_agent(agent_name):
    for section in conf.CONFIG.sections():
        if not section.startswith('agent.'):
            continue

        conf_agent_name = section.split('.', 1)[-1]
        if conf_agent_name != agent_name:
            continue

        agent_url = conf.CONFIG.get(section, 'url')
        return Agent(
            name=agent_name,
            url=agent_url
        )

    return None


def get_agents():
    agents = []
    for section in conf.CONFIG.sections():
        if not section.startswith('agent.'):
            continue

        agent_url = conf.CONFIG.get(section, 'url')
        agent_name = section.split('.', 1)[-1]
        print 'loading agent %s at %s' % (agent_name, agent_url)
        try:
            agents.append(
                Agent(
                    name=agent_name,
                    url=agent_url
                )
            )
        except Exception as exc:
            print exc
            agents.append('Failed to load %s' % agent_name)

    return agents


@app_get('/')
def get():
    agents = get_agents()
    return render_template('index.html', agents=agents)


@app_post('/<agent>/<zone>/actor/<actor>/<prop>')
def set_actor(agent, zone, actor, prop):
    if 'value' not in request.form:
        return 'No value parameter passed', 400

    agent = get_agent(agent)
    if not agent:
        return 'Agent %s not found' % agent, 400

    LOGGER.info(
        'Setting %s for %s.%s.%s as %s'
        % (prop, agent.name, zone, actor, request.form['value'])
    )

    response = requests.post(
        os.path.join(
            agent.url,
            zone,
            'actor',
            actor,
            prop,
        ),
        data=request.form,
    )

    if response.status_code >= 300:
        return response.text, response.status_code

    else:
        return redirect('/')


@app_get('/<agent>/schedule')
def get_schedules(agent):
    agent = get_agent(agent)
    if not agent:
        return 'Agent %s not found' % agent, 400

    return render_template('schedules.html', agent=agent)
