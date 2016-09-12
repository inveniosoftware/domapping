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

"""Test Elasticsearch mapping from jsonschemas."""

import json

import pytest
import responses

from domapping.errors import JsonSchemaSupportError
from domapping.mapping import ElasticMappingGeneratorConfig, schema_to_mapping


def test_simple_properties():
    """Test generation of a very simple mapping"""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'type': 'object',
        'properties': {
            'attr1': {'type': 'string'},
            'attr2': {'type': 'boolean'},
            'attr3': {'type': 'number'},
            'attr4': {'enum': ['Hello', 'world']},
            'attr5': {'enum': [0, 1, 2]},
        },
    }
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'attr1': {'type': 'string'},
            'attr2': {'type': 'boolean'},
            'attr3': {'type': 'double'},
            'attr4': {'type': 'string'},
            'attr5': {'type': 'double'},
        },
    }
    result_mapping = schema_to_mapping(json_schema, json_schema['id'],
                                       {},
                                       ElasticMappingGeneratorConfig())
    assert result_mapping == es_mapping


def test_references():
    """Test mapping generation from a schema containing references."""
    json_schema = {
        'id': 'https://example.org/root_schema.json',
        'type': 'object',
        'properties': {
            'orig': {'type': 'string'},
            'local_ref': {'$ref': '#/properties/orig'},
            'cached_ext_ref': {
                '$ref':
                'https://example.org/cached_external_schema.json#'
                '/definitions/cached_ext_def'
            },
            'ext_ref': {
                '$ref':
                'external_schema.json#/definitions/ext_def'
            },
        },
    }
    cached_external_json_schema = {
        'id': 'https://example.org/cached_external_schema.json',
        'definitions': {
            'cached_ext_def': {'type': 'boolean'},
        },
    }
    non_cached_external_json_schema = {
        'id': 'https://example.org/external_schema.json',
        'definitions': {
            'ext_def': {'type': 'boolean'},
        },
    }
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'orig': {'type': 'string'},
            'local_ref': {'type': 'string'},
            'cached_ext_ref': {'type': 'boolean'},
            'ext_ref': {'type': 'boolean'},
        },
    }
    with responses.RequestsMock() as rsps:
        # serve the external_schema.json file
        rsps.add(responses.GET, 'https://example.org/external_schema.json',
                 body=json.dumps(non_cached_external_json_schema),
                 status=200,
                 content_type='application/json')

        result_mapping = schema_to_mapping(
            json_schema, json_schema['id'], {
                cached_external_json_schema['id']: cached_external_json_schema
            }, ElasticMappingGeneratorConfig())
    assert result_mapping == es_mapping


def test_allOf_anyOf_oneOf():
    """Test mapping generation from a schema containing (all|any|one)Of"""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'anyOf': [{
            'type': 'object',
            'properties': {
                'defined_twice1': {'type': 'string'},
                'allof_attr': {
                    'allOf': [{
                        'type': 'object',
                        'properties': {
                            'attr1': {'type': 'string'},
                            'defined_twice2': {'type': 'string'},
                        },
                    }, {
                        'type': 'object',
                        'properties': {
                            'attr2': {'type': 'boolean'},
                            'defined_twice2': {'type': 'string'},
                        },
                    }]
                },
            },
        }, {
            'type': 'object',
            'properties': {
                'defined_twice1': {'type': 'string'},
                'oneof_attr': {
                    'oneOf': [{
                        'type': 'object',
                        'properties': {
                            'attr3': {'type': 'string'},
                            'defined_twice3': {'type': 'string'},
                        },
                    }, {
                        'type': 'object',
                        'properties': {
                            'attr4': {'type': 'boolean'},
                            'defined_twice3': {'type': 'string'},
                        },
                    }]
                },
            },
        }]
    }
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'defined_twice1': {'type': 'string'},
            'allof_attr': {
                'type': 'object',
                'properties': {
                    'attr1': {'type': 'string'},
                    'attr2': {'type': 'boolean'},
                    'defined_twice2': {'type': 'string'},
                },
            },
            'oneof_attr': {
                'type': 'object',
                'properties': {
                    'attr3': {'type': 'string'},
                    'attr4': {'type': 'boolean'},
                    'defined_twice3': {'type': 'string'},
                },
            },
        },
    }
    result_mapping = schema_to_mapping(json_schema, json_schema['id'],
                                       {},
                                       ElasticMappingGeneratorConfig())
    assert result_mapping == es_mapping


def test_complex_array():
    """Test mapping generation from schema containing a complex array."""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'type': 'object',
        'properties': {
            'myarray': {
                "type": "array",
                "items": [{
                    "type": "object",
                    "properties": {
                        "first_attr": {
                            "type": "string",
                        },
                    },
                }, {
                    "type": "object",
                    "properties": {
                        "second_attr": {
                            "type": "boolean",
                        },
                    },
                }]
            },
            'myarray2': {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "third_attr": {
                            "type": "string",
                        },
                    },
                },
            },
        },
    }
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'myarray': {
                'type': 'object',
                'properties': {
                    'first_attr': {'type': 'string'},
                    'second_attr': {'type': 'boolean'},
                },
            },
            'myarray2': {
                'type': 'object',
                'properties': {
                    'third_attr': {'type': 'string'},
                },
            },
        },
    }
    result_mapping = schema_to_mapping(json_schema, json_schema['id'],
                                       {},
                                       ElasticMappingGeneratorConfig())
    assert result_mapping == es_mapping


def test_depencency_extension():
    """Test ampping generation from schema containing a dependency"""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'type': 'object',
        'properties': {
            "name": {"type": "string"},
        },
        "dependencies": {
            "name": {
                "properties": {
                    "address": {"type": "boolean"}
                },
                "required": ["address"]
            }
        }
    }
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'name': {'type': 'string'},
            'address': {'type': 'boolean'},
        },
    }
    result_mapping = schema_to_mapping(json_schema, json_schema['id'],
                                       {},
                                       ElasticMappingGeneratorConfig())
    assert result_mapping == es_mapping


def test_type_mapping():
    """Test mapping a json type to another elasticsearch type."""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'type': 'object',
        'properties': {
            'attr1': {'type': 'string', 'format': 'custom-date'},
            'attr2': {'type': 'number'},
        },
    }
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'attr1': {'type': 'date', 'format': 'YYYY'},
            'attr2': {'type': 'integer', 'coerce': False},
        }
    }
    config = ElasticMappingGeneratorConfig() \
        .map_type(es_type='integer',
                  json_type='number',
                  es_props={'coerce': False}) \
        .map_type(es_type='date',
                  json_type='string',
                  json_format='custom-date')
    config.date_format = 'YYYY'
    assert config.date_format == 'YYYY'
    result_mapping = schema_to_mapping(json_schema, json_schema['id'],
                                       {}, config)

    assert result_mapping == es_mapping


def test_redefine_attribute():
    """Check that redefining an attribute with a different type fails."""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'type': 'object',
        'anyOf': [{
            'type': 'object',
            'properties': {
                # first definition
                'attr': {'type': 'string'},
            },
        }, {
            'type': 'object',
            'properties': {
                # redefinition
                'attr': {'type': 'boolean'},
            },
        }]
    }
    with pytest.raises(JsonSchemaSupportError):
        schema_to_mapping(json_schema, json_schema['id'],
                          {}, ElasticMappingGeneratorConfig())


def test_additionnalproperties_value_to_false():
    """Check that putting additionalProperties to False doesn't stop."""
    json_schema = {
        'id': 'https://example.org/root_schema#',
        'type': 'object',
        'properties': {
            'attr1': {'type': 'string'},
            'attr2': {'type': 'boolean'},
            'attr3': {'type': 'number'},
            'attr4': {'enum': ['Hello', 'world']},
            'attr5': {'enum': [0, 1, 2]},
        },
        "additionalProperties": False
    }
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'attr1': {'type': 'string'},
            'attr2': {'type': 'boolean'},
            'attr3': {'type': 'double'},
            'attr4': {'type': 'string'},
            'attr5': {'type': 'double'},
        },
    }
    result_mapping = schema_to_mapping(json_schema, json_schema['id'],
                                       {},
                                       ElasticMappingGeneratorConfig())
    assert result_mapping == es_mapping
