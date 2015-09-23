# -*- coding: utf-8 -*-
#
# This file is part of es-jsonschema.
# Copyright (C) 2015 CERN.
#
# es-jsonschema is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# es-jsonschema is distributed in the hope that it will be
# useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with es-jsonschema; if not, write to the Free Software
# Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""es-jsonschema."""

import os
import sys

from setuptools import setup
from setuptools.command.test import test as testcommand

readme = open('readme.rst').read()
history = open('changes.rst').read()

requirements = [
    'jsonpointer>=1.9',
    'jsonschema>=2.5.0',
    'six>=1.7.2',
    'Jinja2>=2.7',
]

test_requirements = [
    'coverage>=3.7.1',
    'pytest-cov>=1.8.0',
    'pytest-pep8>=1.0.6',
    'pytest>=2.7.0',
]


class pytest(testcommand):

    """pytest test."""

    user_options = [('pytest-args=', 'a', "arguments to pass to py.test")]

    def initialize_options(self):
        """init pytest."""
        testcommand.initialize_options(self)
        self.pytest_args = []
        try:
            from ConfigParser import ConfigParser
        except ImportError:
            from ConfigParser import ConfigParser
        config = ConfigParser()
        config.read('setup.cfg')
        self.pytest_args = config.get('pytest', 'addopts').split(' ')

    def finalize_options(self):
        """finalize pytest."""
        testcommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        """run tests."""
        # import here, cause outside the eggs aren't loaded
        import pytest
        import _pytest.config
        pm = _pytest.config.get_plugin_manager()
        pm.consider_setuptools_entrypoints()
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

# get the version string. cannot be done with import!
g = {}
with open(os.path.join('es_jsonschema', 'version.py'), 'rt') \
        as fp:
    exec(fp.read(), g)
    version = g['__version__']

setup(
    name='es-jsonschema',
    version=version,
    description=__doc__,
    long_description=readme + '\n\n' + history,
    keywords='json schema',
    license='gplv2',
    author='invenio software collaboration',
    author_email='info@invenio-software.org',
    # FIXME
    # url='https://github.com/inveniosoftware/es-jsonschema',
    packages=[
        'es_jsonschema',
    ],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=requirements,
    extras_require={
        'docs': [
            'sphinx>=1.3',
            'sphinx_rtd_theme>=0.1.7'
        ],
        'tests': test_requirements
    },
    classifiers=[
        'development status :: 1 - planning',
        'environment :: web environment',
        'intended audience :: developers',
        'license :: osi approved :: gnu general public license v2 (gplv2)',
        'operating system :: os independent',
        'programming language :: python',
        'topic :: internet :: www/http :: dynamic content',
        'topic :: software development :: libraries :: python modules',
        'programming language :: python :: 2',
        'programming language :: python :: 2.7',
    ],
    tests_require=test_requirements,
    cmdclass={'test': pytest},
)
