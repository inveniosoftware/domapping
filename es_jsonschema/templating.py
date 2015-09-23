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

"""Methods pretty printing elasticsearch mappings as jinja templates"""


import json


def es_type_to_jinja(es_mapping, type_name, indent=2):
    """Pretty pring an elasticsearch type mapping as a jinja template

    :param es_mapping: elasticsearch mapping
    :param type_name: name of the elasticsearch type
    :param indent: intentation step
    """
    result = []
    result += '{{\n'.format(type=type_name)
    result += __es_type_to_jinja_rec(es_mapping, type_name, indent,
                                     ' ' * indent)
    result += '}'
    return ''.join(result)


def __es_type_to_jinja_rec(es_mapping, path='', indent=2, start_indent=''):
    """
    Recursively pretty print  an elasticsearch type mapping as a jinja
    template
    """
    result = []
    result += '{i}{{% block {path} %}}\n' \
        .format(i=start_indent, path=path)
    root_idx = 0
    for key, value in es_mapping.iteritems():
        if key == 'properties':
            indent1 = start_indent + ' ' * indent
            result += '{i}"properties": {{\n'.format(i=start_indent)
            result += '{i}{{% block {path}__PROPERTIES__ %}}\n' \
                .format(i=indent1, path=path)
            prop_idx = 0
            for prop_name, prop_schema in value.iteritems():
                result += '{i}"{name}": {{\n'.format(i=indent1, name=prop_name)

                result += __es_type_to_jinja_rec(prop_schema,
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
