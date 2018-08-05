#!/usr/bin/env python
import os
from subprocess import check_output
from setuptools import setup


def get_requires(pkg_name):
    paths = [
        '%s-requires.txt',
        '%s/requires.txt',
    ]
    for path in paths:
        path = path % pkg_name
        if os.path.exists(path):
            return open(path).read().splitlines()

    return ''


common_opts = dict(
    author='David Caro',
    author_email='david@dcaro.es',
    license='GPLv3',
    setup_requires=['autosemver'],
    autosemver=True,
    package_data={
        '': ['LICENSE', '*txt', 'templates/*', 'static/*'],
    },
)

if os.path.exists('domcontrol_common'):
    print 'Installing domcontrol-common...'
    setup(
        name='domcontrol-common',
        description='Domotic sensor and actor control tools, common libs',
        install_requires=get_requires('domcontrol_common'),
        packages=['domcontrol_common'],
        **common_opts
    )
else:
    print (
        'No domcontrol_common dir found, skipping installation of '
        'domcontrol-common...'
    )

if os.path.exists('domcontrol_agent'):
    print 'Installing domcontrol-agent...'
    setup(
        name='domcontrol-agent',
        description='Domotic sensor and actor control tools, agent tools',
        install_requires=get_requires('domcontrol_agent'),
        packages=['domcontrol_agent'],
        entry_points={
            'console_scripts': [
                'domcontrol_agent=domcontrol_agent.cmd:main',
            ],
        },
        **common_opts
    )
else:
    print (
        'No domcontrol_agent dir found, skipping installation of '
        'domcontrol-agent...'
    )

if os.path.exists('domcontrol_master'):
    print 'Installing domcontrol-master...'
    setup(
        name='domcontrol-master',
        description='Domotic sensor and actor control tools, master and ui',
        install_requires=get_requires('domcontrol_master'),
        packages=['domcontrol_master'],
        entry_points={
            'console_scripts': [
                'domcontrol_master=domcontrol_master.cmd:main',
            ],
        },
        **common_opts
    )
else:
    print (
        'No domcontrol_master dir found, skipping installation of '
        'domcontrol-master...'
    )
