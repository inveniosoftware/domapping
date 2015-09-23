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

"""Test Elasticsearch mapping from jsonschemas"""

from es_jsonschema.errors import JsonSchemaSupportError

from es_jsonschema.mapping import \
    ElasticMappingGeneratorConfig, generate_type_mapping

import pytest


class TestMappingGeneration(object):
    """Test the generation of elasticsearch mapping from json schemas"""

    def test_simple_properties(self):
        """Test generation of a very simple mapping"""
        json_schema = {
            'id': 'http://some.site/root_schema#',
            'type': 'object',
            'properties': {
                'attr1': {'type': 'string'},
                'attr2': {'type': 'boolean'},
            },
        }
        es_mapping = {
            '_all': {'enable': True},
            'numeric_detection': True,
            'date_detection': True,
            'properties': {
                'attr1': {'type': 'string'},
                'attr2': {'type': 'boolean'},
            },
        }
        result_mapping = generate_type_mapping(json_schema, json_schema['id'],
                                               {},
                                               ElasticMappingGeneratorConfig())
        assert result_mapping == es_mapping

    def test_type_mapping(self):
        """Test mapping a json type to another elasticsearch type"""
        json_schema = {
            'id': 'http://some.site/root_schema#',
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
        result_mapping = generate_type_mapping(json_schema, json_schema['id'], {
        }, config)

        assert result_mapping == es_mapping

    def test_redefine_attribute(self):
        """Check that redefining an attribute with a different type fails"""
        json_schema = {
            'id': 'http://some.site/root_schema#',
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
            generate_type_mapping(json_schema, json_schema['id'],
                                  {}, ElasticMappingGeneratorConfig())
