# -*- coding: utf-8 -*-
#
# This file is part of JsonSchema-to-ElasticMapping.
# Copyright (C) 2015 CERN.
#
# JsonSchema-to-ElasticMapping is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# JsonSchema-to-ElasticMapping is distributed in the hope that it will be
# useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with JsonSchema-to-ElasticMapping; if not, write to the Free Software
# Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
#
# this file is part of jsonschema-to-elasticmapping.
# copyright (c) 2015 CERN.

"""Test generating jinja template from Elasticsearch mapping"""

import json

import jinja2

from jsonschema_to_elasticmapping.templating import es_type_to_jinja


class TestTemplating(object):
    """Test jinja template generation from Elasticsearch mapping"""

    def test_json_validity(self):
        """Check that the jinja template generates the same json"""
        es_mapping = {
            '_all': {'enable': True},
            'numeric_detection': True,
            'date_detection': True,
            'properties': {
                'attr1': {'type': 'string'},
                'attr2': {'type': 'boolean'},
            },
        }
        expected_result = {
            'mytype': es_mapping,
        }
        jinja_template = es_type_to_jinja(es_mapping, 'mytype')
        es_gen_mapping_str = jinja2.Template(jinja_template).render()
        es_gen_mapping = json.loads('{' + es_gen_mapping_str + '}')
        assert expected_result == es_gen_mapping
