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

"""Methods pretty printing elasticsearch mappings as jinja templates."""

import json

import jinja2
from six import iteritems

from .mapping import clean_mapping


def mapping_to_jinja(es_mapping, type_name, indent=2, start_indent=''):
    """Pretty pring an elasticsearch type mapping as a jinja template.

    :param es_mapping: elasticsearch mapping
    :param type_name: name of the elasticsearch type
    :param indent: intentation step
    :param start_indent: base indent
    """
    result = []
    result += '{{\n'.format(type=type_name)
    result += _mapping_to_jinja_rec(es_mapping, type_name, indent,
                                    start_indent + ' ' * indent)
    result += start_indent + '}'
    return ''.join(result)


def _mapping_to_jinja_rec(es_mapping, path='', indent=2, start_indent=''):
    """Pretty print an elasticsearch type mapping as a jinja template.

    The printing is recursive.
    """
    result = []
    result += '{i}{{% block {path} %}}\n' \
        .format(i=start_indent, path=path)
    root_idx = 0
    for key, value in iteritems(es_mapping):
        if key == 'properties':
            indent1 = start_indent + ' ' * indent
            result += '{i}"properties": {{\n'.format(i=start_indent)
            result += '{i}{{% block {path}__PROPERTIES__ %}}\n' \
                .format(i=indent1, path=path)
            prop_idx = 0
            for prop_name, prop_schema in iteritems(value):
                result += '{i}"{name}": {{\n'.format(i=indent1, name=prop_name)

                result += _mapping_to_jinja_rec(prop_schema,
                                                path + '__' + prop_name,
                                                indent,
                                                indent1 + ' ' * indent)

                result += '{i}}}{sep}\n' \
                    .format(i=indent1,
                            sep=(',' if prop_idx < len(value) - 1 else ''))
                prop_idx += 1
            result += '{i}{{% endblock %}}\n'.format(i=indent1)
            result += '{i}}}'.format(i=start_indent)
        else:
            result += '{i}"{name}": {val}'.format(i=start_indent,
                                                  name=key,
                                                  val=json.dumps(value))
        result += '{sep}\n'.format(
            sep=(',' if root_idx < len(es_mapping) - 1 else ''))
        root_idx += 1
    result += '{i}{{% endblock %}}\n' \
        .format(i=start_indent)
    return result


def jinja_to_mapping(template, context_paths=None, context_packages=None):
    """Generate Elasticsearch mapping from jinja import templates.

    :param template: jinja template
    :param context_packages: Context templates. It can either be a directory
        containing jinja files or a jinja file.
    :param context_paths: Context templates. It must be an existing package
        name followed by the path to the templates in that package.

    :return: the resulting mapping
    :rtype: dict
    """
    # Create jinja environment. It will search for all templates in the
    # given path and packages
    if context_packages:
        jinja_loaders = [jinja2.PackageLoader(package, path)
                         for package, path in context_packages]
    else:
        jinja_loaders = []

    if context_paths:
        jinja_loaders.append(jinja2.FileSystemLoader(context_paths))
    jinja_env = jinja2.Environment(loader=jinja2.ChoiceLoader(jinja_loaders))

    # generate the mapping from the import jinja template
    mapping_str = jinja_env.from_string(template).render()
    # parse the mapping and clean it (remove keys with null values)
    return clean_mapping(json.loads(mapping_str))
