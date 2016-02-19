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
import pytest
from click.testing import CliRunner

from domapping.cli import jinja_to_mapping_cli, mapping_to_jinja_cli, \
    schema_to_mapping_cli
from domapping.errors import JsonSchemaSupportError, UnknownFieldTypeError


def assert_exception(result, expected_exception):
    """Assert that a cli result has the expected exception.

    If the exception is different and there is an exception the stack trace,
    it is printed.
    """
    if result.exception and isinstance(result.exception, expected_exception):
        traceback.print_exception(*result.exc_info)
    assert isinstance(result.exception, expected_exception)


def assert_no_exception(result):
    """Assert that a cli result has no exception.

    If there is an exception the stack trace is printed.
    """
    if result.exception:
        traceback.print_exception(*result.exc_info)
    assert not result.exception

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


@pytest.mark.parametrize(
    'src_schema, schemas, config, expected_mapping,'
    'expected_exception,test_stream',
    [
        # simple schema test
        (
            'schema.json',
            {
                'schema.json': {
                    'id': 'https://example.org/root_schema#',
                    'type': 'object',
                    'properties': {
                        'name': {'type': 'string'},
                        'nb': {'type': 'number'},
                        'creation_date':
                        {'type': 'string', 'format': 'mydate'}
                    },
                },
            },
            config,
            expected_mapping,
            None,
            True,
        ),
        # multiple schema files without id and with relative references.
        (
            'schema.json',
            {
                'schema.json': {
                    'type': 'object',
                    'properties': {
                        'name': {'$ref':
                                 'subschema.json#/definitions/subname'},
                        'nb': {'type': 'number'},
                        'creation_date': {
                            '$ref': 'subschema.json#/definitions/subdate'}
                    },
                },
                'subschema.json': {
                    'definitions': {
                        'subname': {
                            '$ref':
                            'subsubschema.json#/definitions/subsubname'},
                        'subdate': {
                            '$ref':
                            'subsubschema.json#/definitions/subsubdate'},
                    },
                },
                'subsubschema.json': {
                    'definitions': {
                        'subsubname': {'type': 'string'},
                        'subsubdate': {'type': 'string', 'format': 'mydate'},
                    },
                },
            },
            config,
            expected_mapping,
            None,
            False,
        ),
        # test guessing field type from enum array.
        (
            'schema.json',
            {
                'schema.json': {
                    'id': 'https://example.org/root_schema#',
                    'type': 'object',
                    'properties': {
                        'name': {
                            'enum': ["value 1", "value 2", "value 3"]
                        },
                        'nb': {'type': 'number'},
                        'creation_date':
                        {'type': 'string', 'format': 'mydate'}
                    },
                },
            },
            config,
            expected_mapping,
            None,
            False,
        ),
        # Guessing from enum with non 'string' fields should fail.
        (
            'schema.json',
            {
                'schema.json': {
                    'id': 'https://example.org/root_schema#',
                    'type': 'object',
                    'properties': {
                        'name': {
                            'enum': ["value 1", "value 2", 3]
                        },
                    },
                },
            },
            config,
            None,
            UnknownFieldTypeError,
            False,
        ),
        # Guessing type with just format is not allowed and should fail.
        (
            'schema.json',
            {
                'schema.json': {
                    'id': 'https://example.org/root_schema#',
                    'type': 'object',
                    'properties': {
                        'name': {
                            'format': 'not important'
                        },
                    },
                },
            },
            config,
            None,
            UnknownFieldTypeError,
            False,
        ),
    ])
def test_schema_to_mapping(src_schema, schemas, config, expected_mapping,
                           expected_exception, test_stream):
    """Test schema_to_mapping."""
    config_file = 'config.json'

    runner = CliRunner()
    with runner.isolated_filesystem():
        # write the config file
        with open(config_file, 'w') as f:
            f.write(json.dumps(config))

        for path, schema in schemas.items():
            with open(path, 'w') as f:
                f.write(json.dumps(schema))
        result = runner.invoke(
            schema_to_mapping_cli,
            [src_schema, '-', '--config', config_file],
        )
        if expected_exception:
            assert_exception(result, expected_exception)
        else:
            assert_no_exception(result)
            assert json.loads(result.output) == expected_mapping

        if test_stream:
            # test with a stream instead of a file
            result = runner.invoke(
                schema_to_mapping_cli,
                ['-', '-', '--config', config_file],
                input=json.dumps(schemas[src_schema]),
            )
            if expected_exception:
                assert_exception(result, expected_exception)
            else:
                assert_no_exception(result)
                assert json.loads(result.output) == expected_mapping

                # test with a stream instead of a file and no id
                modified_schema = copy.deepcopy(schemas[src_schema])
                del modified_schema['id']
                result = runner.invoke(
                    schema_to_mapping_cli,
                    ['-', '-', '--config', config_file],
                    input=json.dumps(modified_schema),
                )
                assert type(result.exception) == JsonSchemaSupportError

        # Test of `final` parameter
        result = runner.invoke(
                schema_to_mapping_cli,
                ['-t', 'schema', '--config', config_file, src_schema])
        if expected_exception:
            assert_exception(result, expected_exception)
        else:
            assert_no_exception(result)
            assert json.loads(result.output) == {
                'mappings': {
                    'schema': expected_mapping
                }
            }


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
        ['-', '-', '--mapping-type', type_name],
        input=json.dumps(mapping),
    )

    assert_no_exception(result)
    # use the child template to modify the output template.
    jinja_env = jinja2.Environment(
        loader=jinja2.DictLoader({'generated': result.output}))
    gen_output = json.loads(jinja_env.from_string(child_template).render())
    assert gen_output == expected


def test_multiple_mapping_to_jinja():
    """Test mapping_to_jinja with a valid mapping containing multiple.

    Check mapping_to_jinja with a valid mapping containing multiple.
    """
    mapping = {
        "mappings": {
            "test1": {
                "properties": {
                    'sub1': {
                        'type': 'string',
                    }
                }
            },
            "test2": {
                "properties": {
                    'sub2': {
                        'type': 'string',
                    }
                }
            }
        }
    }

    # template which extends the generated one and will be compiled.
    child_template = """
    {% extends "generated"%}

    {% block test1 %}
    {{ super() }},
    "top_attr": "top_value"
    {%endblock%}

    {% block test1__PROPERTIES__ %}
    {{ super() }},
    "prop_attr": "prop_value"
    {%endblock%}

    {% block test1__sub1 %}
    {{ super() }},
    "sub1_attr": "sub1_value"
    {%endblock%}

    {% block test2 %}
    {{ super() }},
    "top_attr": "top_value"
    {%endblock%}

    {% block test2__PROPERTIES__ %}
    {{ super() }},
    "prop_attr": "prop_value"
    {%endblock%}

    {% block test2__sub2 %}
    {{ super() }},
    "sub2_attr": "sub2_value"
    {%endblock%}
    """

    # build expected output
    expected = copy.deepcopy(mapping)
    expected['mappings']['test1']['top_attr'] = 'top_value'
    expected['mappings']['test1']['properties']['prop_attr'] = 'prop_value'
    expected['mappings']['test1']['properties']['sub1'] = {
        'sub1_attr': 'sub1_value',
        'type': 'string'
    }
    expected['mappings']['test2']['top_attr'] = 'top_value'
    expected['mappings']['test2']['properties']['prop_attr'] = 'prop_value'
    expected['mappings']['test2']['properties']['sub2'] = {
        'sub2_attr': 'sub2_value',
        'type': 'string'
    }

    runner = CliRunner()

    result = runner.invoke(
        mapping_to_jinja_cli,
        ['-', '-'],
        input=json.dumps(mapping),
    )

    assert_no_exception(result)
    # use the child template to modify the output template.
    jinja_env = jinja2.Environment(
        loader=jinja2.DictLoader({'generated': result.output}))
    content = jinja_env.from_string(child_template).render()
    gen_output = json.loads(content)
    assert gen_output == expected


def test_mapping_to_jinja_inconsistencies():
    """Test mapping_to_jinja.

    Check that mapping_to_jinja fails if --mapping-type is set when it is
    called on a mapping having multiple types in it.
    """
    mapping = {
        "mappings": {
            "test1": {
                "properties": {
                    'sub1': {
                        'type1': 'string',
                    }
                }
            },
            "test2": {
                "properties": {
                    'sub2': {
                        'type2': 'string',
                    }
                }
            }
        }
    }
    runner = CliRunner()

    result = runner.invoke(
        mapping_to_jinja_cli,
        ['-', '-', '--mapping-type', 'mytype'],
        input=json.dumps(mapping),
    )

    assert_exception(result, AssertionError)


def test_mapping_to_jinja_wo_type():
    """Test mapping_to_jinja with a valid single type mapping

    Check mapping_to_jinja with a valid single type mapping not included in
    a "mappings" dict.
    """
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

    {% block type %}
    {{ super() }},
    "top_attr": "top_value"
    {%endblock%}

    {% block type__PROPERTIES__ %}
    {{ super() }},
    "prop_attr": "prop_value"
    {%endblock%}

    {% block type__nb %}
    {{ super() }},
    "nb_attr": "nb_value"
    {%endblock%}

    {% block type__obj %}
    {{ super() }},
    "obj_attr": "obj_value"
    {%endblock%}

    {% block type__obj__PROPERTIES__ %}
    {{ super() }},
    "obj_prop_attr": "obj_prop_value"
    {%endblock%}

    {% block type__obj__sub %}
    {{ super() }},
    "obj_sub_attr": "obj_sub_value"
    {%endblock%}

    {% block type__name %}
    {{ super() }},
    "name_attr": "name_value"
    {%endblock%}
    }"""

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
        ['-', '-'],
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
