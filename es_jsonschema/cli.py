# -*- coding: utf-8 -*-
#
# This file is part of es-jsonschema.
# Copyright (C) 2015 CERN.
#
# es-jsonschema is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# es-jsonschema is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with es-jsonschema; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""CLI commands."""

import json

import click

from .errors import JsonSchemaSupportError
from .mapping import ElasticMappingGeneratorConfig, schema_to_mapping
from .templating import jinja_to_mapping, mapping_to_jinja


@click.group()
def cli():
    """CLI group."""
    pass  # pragma: no cover


@cli.command('schema_to_mapping')
@click.argument('schema', type=click.File('r'), default='-')
@click.argument('output', type=click.File('w'), default='-')
@click.option('--config', '-c',
              type=click.Path(exists=True, dir_okay=False, file_okay=True),
              help='Mapping generation configuration.')
@click.option('--indent', '-i', default=4, type=click.INT,
              help='Output json indentation step.')
def schema_to_mapping_cli(schema, output, config, indent):
    """Generate Elasticsearch mapping from json-schema."""
    parsed_schema = json.load(schema)

    if 'id' not in parsed_schema and not hasattr(schema, 'name'):
        raise JsonSchemaSupportError('json-schema does not contain any '
                                     '\'id\' field and input has no name',
                                     '<INPUT>')
    id = parsed_schema.get('id',
                           schema.name if hasattr(schema, 'name') else None)

    config_instance = ElasticMappingGeneratorConfig()
    if config:
        with open(config) as conf:
            config_instance.load(json.load(conf))

    mapping = schema_to_mapping(parsed_schema, id, {}, config_instance)
    json.dump(mapping, output, indent=indent)


@cli.command('mapping_to_jinja')
@click.argument('mapping', type=click.File('r'), default='-')
@click.argument('output', type=click.File('w'), default='-')
@click.option('--indent', '-i', default=4, type=click.INT,
              help='Output template indentation step.')
@click.option('--type', '-t', default='type', type=click.STRING,
              help='Root type name used in jinja block names.')
def mapping_to_jinja_cli(mapping, output, indent, type):
    """Generate jinja template from Elasticsearch mapping."""
    parsed_mapping = json.load(mapping)

    template = mapping_to_jinja(parsed_mapping, type, indent=indent)
    output.write(template)


@cli.command('jinja_to_mapping')
@click.argument('template', type=click.File('r'), default='-')
@click.argument('output', type=click.File('w'), default='-')
@click.option('--context_path', multiple=True,
              help='Context templates. It can either be a directory ' +
              'containing jinja files or a jinja file.',
              type=click.Path(dir_okay=True, file_okay=True, exists=True))
@click.option('--context_package', multiple=True, nargs=2,
              help='Context templates. It must be an existing package name ' +
              'followed by the path to the templates in that package.',
              type=click.Tuple([click.STRING, click.STRING]))
@click.option('--indent', '-i', default=4, type=click.INT,
              help='Output template indentation step.')
def jinja_to_mapping_cli(template, output, context_path, context_package,
                         indent):
    """Generate Elasticsearch mapping from jinja import templates."""
    result = jinja_to_mapping(template.read(), context_path, context_package)
    # dump the mapping to the output
    json.dump(result, output, indent=indent)
