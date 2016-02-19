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

"""CLI commands."""

import json
import os
import sys

import click
from six.moves import urllib

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
@click.option('--mapping-type', '-t',
              help='ElasticSearch mapping type.')
def schema_to_mapping_cli(schema, output, config, indent, mapping_type):
    """Generate Elasticsearch mapping from JSON Schema."""
    file_url = None
    if schema != sys.stdin and hasattr(schema, 'name'):
        assert os.path.isfile(schema.name)
        file_url = ('file://' +
                    urllib.request.pathname2url(os.path.abspath(schema.name)))

    parsed_schema = json.load(schema)

    if 'id' not in parsed_schema and not file_url:
        raise JsonSchemaSupportError('JSON Schema does not contain any '
                                     '\'id\' field and input is not a file',
                                     '<INPUT>')
    id = parsed_schema.get('id',
                           file_url)

    config_instance = ElasticMappingGeneratorConfig()
    if config:
        with open(config) as conf:
            config_instance.load(json.load(conf))

    mapping = schema_to_mapping(parsed_schema, id, {}, config_instance)
    if mapping_type is not None:
        mapping = {
            'mappings': {
                mapping_type: mapping
            }
        }
    json.dump(mapping, output, indent=indent)


@cli.command('mapping_to_jinja')
@click.argument('mapping', type=click.File('r'), default='-')
@click.argument('output', type=click.File('w'), default='-')
@click.option('--indent', '-i', default=4, type=click.INT,
              help='Output template indentation step.')
@click.option('--mapping-type', '-t', type=click.STRING,
              help='Root type name used in jinja block names.')
def mapping_to_jinja_cli(mapping, output, indent, mapping_type):
    """Generate jinja template from Elasticsearch mapping."""
    default_type = 'type'
    parsed_mapping = json.load(mapping)

    if 'mappings' in parsed_mapping:
        n_mappings = len(parsed_mapping['mappings'])
        assert not (n_mappings > 1 and mapping_type)

        result = []
        for item in parsed_mapping['mappings']:
            template = mapping_to_jinja(
                    parsed_mapping['mappings'][item],
                    item if n_mappings != 1 or
                    not mapping_type else mapping_type,
                    indent=indent, start_indent=' ' * indent * 2)
            result.append('{0}"{1}":{2}'.format(
                    indent * 2 * ' ', item, template))
        output.write('{{\n'
                     '{0}"mappings": {{\n'
                     '{1}\n'
                     '{0}}}\n'
                     '}}'.format(indent * ' ', ',\n'.join(result)))
    else:
        if not mapping_type:
            mapping_type = default_type
        template = mapping_to_jinja(
                parsed_mapping, mapping_type, indent=indent)
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
