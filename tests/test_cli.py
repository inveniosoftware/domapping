# -*- coding: utf-8 -*-
#
# This file is part of DoMapping.
# Copyright (C) 2015, 2016 CERN.
#
# DoMapping is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# DoMapping is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DoMapping; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Tests of domapping.cli."""

import copy
import json
import os
import sys
import traceback

import jinja2
from click.testing import CliRunner

from domapping.cli import jinja_to_mapping_cli, mapping_to_jinja_cli, \
    schema_to_mapping_cli
from domapping.errors import JsonSchemaSupportError


def assert_no_exception(result):
    """Assert that a cli result has no exception.

    If there is an exception the stack trace is printed.
    """
    if result.exception:
        traceback.print_exception(*result.exc_info)
    assert not result.exception


def test_schema_to_mapping():
    """Test schema_to_mapping."""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'nb': {'type': 'number'},
            "creation_date": {"type": "string", "format": "mydate"}
        },
    }

    expected_mapping = {
        "_all": {
            "enable": False,
        },
        "numeric_detection": False,
        "properties": {
            "nb": {
                "type": "short",
                "store": True,
            },
            "name": {
                "type": "string",
            },
            "creation_date": {
                "type": "date",
                "format": "YYYY",
            }
        },
        "date_detection": False,
    }
    schema_file = 'schema.json'

    config = {
        'types': [{
            'json_type': 'string',
            'json_format': 'mydate',
            'es_type': 'date',
        }, {
            'json_type': 'number',
            'es_type': 'short',
            'es_props': {
                'store': True
            },
        }],
        'date_format': 'YYYY',
        'date_detection': False,
        'numeric_detection': False,
        'all_field': False,
    }
    config_file = 'config.json'

    runner = CliRunner()
    with runner.isolated_filesystem():
        # write the config file
        with open(config_file, 'w') as f:
            f.write(json.dumps(config))

        result = runner.invoke(
            schema_to_mapping_cli,
            ['-', '-', '--config', config_file],
            input=json.dumps(json_schema),
        )
        assert_no_exception(result)
        assert json.loads(result.output) == expected_mapping

        # test again but without id in schema
        del json_schema['id']
        # write the schema file
        with open(schema_file, 'w') as f:
            f.write(json.dumps(json_schema))
        result = runner.invoke(
            schema_to_mapping_cli,
            [schema_file, '-', '--config', config_file],
            input=json.dumps(json_schema),
        )
        assert_no_exception(result)
        assert json.loads(result.output) == expected_mapping

        # test again without id in schema and with a stream which has no
        # name property (i.e: StringIO)
        result = runner.invoke(
            schema_to_mapping_cli,
            ['-', '-', '--config', config_file],
            input=json.dumps(json_schema),
        )
        assert type(result.exception) == JsonSchemaSupportError


def test_mapping_to_jinja():
    """Test mapping_to_jinja."""
    mapping = {
        "_all": {
            "enable": False,
        },
        "numeric_detection": False,
        "properties": {
            "nb": {
                "type": "short",
                "store": True,
            },
            "obj": {
                "type": "object",
                "properties": {
                    'sub': {
                        'type': 'string',
                    }
                },
            },
            "name": {
                "type": "string",
            },
        },
        "date_detection": False,
    }

    # template which extends the generated one and will be compiled.
    child_template = """
    {% extends "generated"%}

    {% block mytype %}
    {{ super() }},
    "top_attr": "top_value"
    {%endblock%}

    {% block mytype__PROPERTIES__ %}
    {{ super() }},
    "prop_attr": "prop_value"
    {%endblock%}

    {% block mytype__nb %}
    {{ super() }},
    "nb_attr": "nb_value"
    {%endblock%}

    {% block mytype__obj %}
    {{ super() }},
    "obj_attr": "obj_value"
    {%endblock%}

    {% block mytype__obj__PROPERTIES__ %}
    {{ super() }},
    "obj_prop_attr": "obj_prop_value"
    {%endblock%}

    {% block mytype__obj__sub %}
    {{ super() }},
    "obj_sub_attr": "obj_sub_value"
    {%endblock%}

    {% block mytype__name %}
    {{ super() }},
    "name_attr": "name_value"
    {%endblock%}
    }"""

    type_name = 'mytype'

    # build expected output
    expected = copy.deepcopy(mapping)
    expected['top_attr'] = 'top_value'
    expected['properties']['prop_attr'] = 'prop_value'
    expected['properties']['nb']['nb_attr'] = 'nb_value'
    expected['properties']['obj']['obj_attr'] = 'obj_value'
    expected['properties']['obj']['properties']['obj_prop_attr'] = \
        'obj_prop_value'
    expected['properties']['obj']['properties']['sub']['obj_sub_attr'] = \
        'obj_sub_value'
    expected['properties']['name']['name_attr'] = 'name_value'

    runner = CliRunner()

    result = runner.invoke(
        mapping_to_jinja_cli,
        ['-', '-', '--type', type_name],
        input=json.dumps(mapping),
    )

    assert_no_exception(result)
    # use the child template to modify the output template.
    jinja_env = jinja2.Environment(
        loader=jinja2.DictLoader({'generated': result.output}))
    gen_output = json.loads(jinja_env.from_string(child_template).render())

    assert gen_output == expected


def test_jinja_to_mapping():
    """Test jinja_to_mapping."""
    root_template = """
    {
    "my root": "sentence",
    "to remove": "non null value",
    {% block overriden %}
    "my overriden": "sentence"
    {% endblock %}
    }
    """
    root_template_package = 'mypackage'
    root_template_directory = 'templates'
    root_template_subdirectory = 'sub'
    root_template_file = 'root.json'

    child_template = """
    {{% extends "{root}" %}}

    {{% block overriden %}}
    "my child": "sentence",
    "to remove": null
    {{% endblock %}}
    """.format(root=os.path.join(root_template_subdirectory,
                                 root_template_file))
    child_template_file = 'child.json'

    expected_output = {
        "my root": "sentence",
        "my child": "sentence"
    }

    runner = CliRunner()
    with runner.isolated_filesystem():
        os.makedirs(os.path.join(root_template_package,
                                 root_template_directory,
                                 root_template_subdirectory))
        # write the child template file
        with open(os.path.join(root_template_package,
                               root_template_directory,
                               root_template_subdirectory,
                               root_template_file), 'w') as f:
            f.write(root_template)

        with open(child_template_file, 'w') as f:
            f.write(child_template)

        # test with context_path
        result = runner.invoke(
            jinja_to_mapping_cli,
            [child_template_file, '-', '--context_path',
                os.path.join(root_template_package, root_template_directory)],
        )
        assert_no_exception(result)
        assert json.loads(result.output) == expected_output

        # create and add the package
        with open(os.path.join(root_template_package,
                               '__init__.py'), 'a') as f:
            pass
        sys.path.append(os.getcwd())

        # test with context_package
        result = runner.invoke(
            jinja_to_mapping_cli,
            [child_template_file, '-', '--context_package',
                root_template_package, root_template_directory],
        )
        assert_no_exception(result)
        assert json.loads(result.output) == expected_output
