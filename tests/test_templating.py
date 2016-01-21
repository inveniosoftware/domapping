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

"""Test generating jinja template from Elasticsearch mapping."""

import json

import jinja2

from domapping.templating import mapping_to_jinja


def test_json_validity():
    """Check that the jinja template generates the same json."""
    es_mapping = {
        '_all': {'enable': True},
        'numeric_detection': True,
        'date_detection': True,
        'properties': {
            'attr1': {'type': 'string'},
            'attr2': {'type': 'boolean'},
        },
    }
    jinja_template = mapping_to_jinja(es_mapping, 'mytype')
    es_gen_mapping_str = jinja2.Template(jinja_template).render()
    es_gen_mapping = json.loads(es_gen_mapping_str)
    assert es_mapping == es_gen_mapping
