#!/usr/bin/env python
import os
from subprocess import check_output
from setuptools import setup



def get_version():
    """
    Retrieves the version of the package, from the PKG-INFO file or generates
    it with the version script
    Returns:
        str: Version for the package
    Raises:
        RuntimeError: If the version could not be retrieved
    """
    version = None
    if os.path.exists('PKG-INFO'):
        with open('PKG-INFO') as info_fd:
            for line in info_fd.readlines():
                if line.startswith('Version: '):
                    version = line.split(' ', 1)[-1].strip()

    elif os.path.exists('scripts/version_manager.py'):
        version = check_output(
            [
                'scripts/version_manager.py',
                '.',
                'version',
            ]
        ).strip()

    if version is None:
        raise RuntimeError('Failed to get package version')

    return version


def get_requires(pkg_name):
    paths = [
        '%s-requires.txt',
        '%s/requires.txt',
    ]
    for path in paths:
        if os.path.exists(path):
            return open(path).read()

    return ''


common_opts = dict(
    author='David Caro',
    author_email='david@dcaro.es',
    license='GPLv3',
    setup_requires=['dulwich'],
    version=get_version(),
    package_data={
        '': ['LICENSE', '*txt'],
    },
)

if os.path.exists('domcontrol_common'):
    setup(
        name='domcontrol_common',
        description='Domotic sensor and actor control tools, common libs',
        install_requires=get_requires('domcontrol_common'),
        packages=['domcontrol_common'],
        **common_opts
    )

if os.path.exists('domcontrol_agent'):
    setup(
        name='domcontrol_agent',
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

if os.path.exists('domcontrol_master'):
    setup(
        name='domcontrol_master',
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
