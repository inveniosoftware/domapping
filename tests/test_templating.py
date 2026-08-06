# SPDX-FileCopyrightText: 2015, 2016 CERN.
# SPDX-License-Identifier: MIT

"""Test generating jinja template from Elasticsearch mapping."""

import json

import jinja2

from domapping.templating import mapping_to_jinja


def test_json_validity():
    """Check that the jinja template generates the same json."""
    es_mapping = {
        "_all": {"enable": True},
        "numeric_detection": True,
        "date_detection": True,
        "properties": {
            "attr1": {"type": "string"},
            "attr2": {"type": "boolean"},
        },
    }
    jinja_template = mapping_to_jinja(es_mapping, "mytype")
    es_gen_mapping_str = jinja2.Template(jinja_template).render()
    es_gen_mapping = json.loads(es_gen_mapping_str)
    assert es_mapping == es_gen_mapping
