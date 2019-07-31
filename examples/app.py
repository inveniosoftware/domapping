# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Minimal Flask application example for development.

Run this example:

.. code-block:: console

    $ cd examples
    $ python app.py

The same result could be created with the cli:

.. code-block:: console

    $ cd examples
    $ mkdir generated
    $ domapping schema_to_mapping schema.json --config config.json | \
        domapping mapping_to_jinja > generated/generated_schema.json
    $ domapping jinja_to_mapping template.json --context_path generated
"""

from __future__ import absolute_import, print_function

import json
import os

from domapping.mapping import ElasticMappingGeneratorConfig, schema_to_mapping
from domapping.templating import jinja_to_mapping, mapping_to_jinja

config = ElasticMappingGeneratorConfig()

with open('schema.json') as schema_file:
    # read the schema
    schema = json.load(schema_file)

with open('config.json') as config_file:
    # load the configuration file
    config.load(json.load(config_file))

# generate the intermediate mapping
mapping = schema_to_mapping(schema, schema['id'], {}, config)

print('>> Intermediate mapping')
print(json.dumps(mapping, indent=4))
print('=' * 50)

# generate the jinja template
generated_template = mapping_to_jinja(mapping, 'person')

generated_template_dir = 'generated'
if not os.path.exists(generated_template_dir):
    os.mkdir(generated_template_dir)

generated_template_path = os.path.join(
    generated_template_dir,
    'generated_schema.json'
)

# write the template to a file so that it can be used by jinja
with open(generated_template_path, 'w') as gen_schema_file:
    gen_schema_file.write(generated_template)

# generate the final mapping from a import template overriding blocks
# of the generated one
with open('template.json') as overriding_template_file:
    overriding_template = overriding_template_file.read()

final_mapping = jinja_to_mapping(overriding_template,
                                 context_paths=[generated_template_dir])

print('>> Final mapping')
print(json.dumps(final_mapping, indent=4))
