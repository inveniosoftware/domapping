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

"""Elastic Search integration. mapping funtion"""

import jsonschema

from jsonschema_to_elasticmapping.errors import JsonSchemaSupportError


class ElasticMappingGeneratorConfig(object):
    """Configuration used during elasticsearch mapping generation."""
    def __init__(self, *args, **kwargs):
        super(ElasticMappingGeneratorConfig, self).__init__(*args, **kwargs)
        # json type -> elasticsearch type
        # this contains the default string mapping when no format matches
        self.__types_map = {
            'string': {'type': 'string'},
            'number': {'type': 'double'},
            'integer': {'type': 'integer'},
            'boolean': {'type': 'boolean'},
        }
        # json string formats -> elasticsearch type
        self.__formats_map = {}

    def map_type(self, es_type, json_type, json_format=None, es_props=None):
        """Map a json schema type (with optionally a format if it is a string)
        to an elasticsearch type.

        :param es_type: elasticsearch type
        :param json_type: json schema type
        :param json_format: json schema format (when the type is string).
            Mapping "string" type without specifying a format sets the default
            mapping.
        :param es_props: additional properties linked to the elasticsearch type
            as a python dict. All its values will be copied in corresponding
            property mappings with the type. Example: { 'format': 'YYYY' }
        """
        assert json_type in ['string', 'boolean', 'number', 'integer']

        stored_mapping = {
            'type': es_type,
            'props': es_props
        }

        if json_type == 'string' and json_format:
            self.__formats_map[json_format] = stored_mapping
        else:
            self.__types_map[json_type] = stored_mapping
        return self

    def get_es_type(self, json_type, json_format=None):
        if (json_type == 'string' and json_format and
                json_format in self.__formats_map):
            stored = self.__formats_map.get(json_format)
        else:
            stored = self.__types_map[json_type]
        props = stored.get('props') or {}
        if (stored['type'] == 'date' and 'format' not in props):
            props['format'] = self.__date_format
        return (stored['type'], props)

    @property
    def date_format(self):
        return getattr(self, '__date_format', None)

    @date_format.setter
    def date_format(self, date_format):
        self.__date_format = date_format
        return self

    @property
    def all_field(self):
        return getattr(self, '__all_field', True)

    @all_field.setter
    def all_field(self, enabled):
        self.__all_field = enabled
        return self

    @property
    def date_detection(self):
        return getattr(self, '__date_detection', True)

    @date_detection.setter
    def date_detection(self, enabled):
        self.__date_detection = enabled
        return self

    @property
    def numeric_detection(self):
        return getattr(self, '__numeric_detection', True)

    @numeric_detection.setter
    def numeric_detection(self, enabled):
        self.__numeric_numeric = enabled
        return self


def generate_type_mapping(json_schema, base_uri, context_schemas, config):
    """Generate an elasticsearch type properties' mapping corresponding to the
    given json schema. It generates only the "type" and "properties" fields.

    :param json_schema: json schema used to generate the elasticsearch mapping
    :param base_uri: json path pointing to the given json_schema. Used for debug.
    :param context_schemas: dict of schema_id -> schema used to resolve
        references.
    :param config: configuration used to generate the elasticsearch mapping.
    """
    resolver = jsonschema.RefResolver(referrer=json_schema,
                                      store=context_schemas,
                                      base_uri=base_uri)
    return __gen_type_properties(json_schema, base_uri, resolver, config, {
        '_all': config.all_field,
        'numeric_detection': config.numeric_detection,
        'date_detection': config.date_detection,
        # empty type mapping
        'properties': {},
    })


__collection_keys = frozenset(['allOf', 'anyOf', 'oneOf'])


def __gen_type_properties(json_schema, path, resolver, config, es_mapping):
    """Generate recursively an elasticsearch type properties' mapping
    corresponding to the given json schema. It generates only the "type" and
    "properties" fields.

    :param json_schema: json schema used to generate the elasticsearch mapping
    :param path: json path pointing to the given json_schema. Used for debug.
    :param resolver: jsonschema resolver used to retrieve referenced schemas.
    :param config: configuration used to generate the elasticsearch mapping.
    :param es_mapping: elasticsearch mapping corresponding to the given schema.
        It is necessary as multiple paths in the json schema may point to the
        same elasticsearch mapping element.
    """
    has_scope = 'id' in json_schema
    # update the current scope if the schema has an id
    if has_scope:
        resolver.push_scope(json_schema.get('id'))

    # resolve reference if there are any
    while '$ref' in json_schema:
        path = json_schema.get('$ref')
        json_schema = resolver.resolve(path)[1]

    if 'patternProperties' in json_schema:
        raise JsonSchemaSupportError('Schemas with patternProperties ' +
                                     'are not supported.', path)
    if 'additionalProperties' in json_schema:
        raise JsonSchemaSupportError('Schemas with ' +
                                     'additionalProperties are not ' +
                                     'supported.', path)

    if es_mapping is None:
        es_mapping = {}

    # if the schema is in fact a collection of schemas, merge them
    json_schema_keys = set(json_schema.keys())
    collection_intersect = json_schema_keys.intersection(__collection_keys)
    if collection_intersect:
        # we suppose the schema is valid and only one of the collection keys
        # is present
        collection_key = collection_intersect.pop()
        # visit each schema and use it to extend current elasticsearch
        # mapping
        path += '/' + collection_key
        index = 0
        for sub_schema in json_schema.get(collection_key):
            __gen_type_properties(sub_schema, path + '[' + str(index) + ']',
                                  resolver, config, es_mapping)
            index += 1
        return es_mapping

    # get json schema type
    json_type = json_schema.get('type')

    if not json_type:
        if 'properties' in json_schema:
            json_type = 'object'
        else:
            # FIXME: handle enums with no type
            raise JsonSchemaSupportError('Schema has no "type" field', path)

    if isinstance(json_type, list):
        raise JsonSchemaSupportError('Schema with array of types are ' +
                                     'not supported', path)

    if json_type == 'array':
        items = json_schema.get('items')
        # array items type is mandatory
        if not items:
            raise JsonSchemaSupportError('Cannot have schema with ' +
                                         '"array" type without ' +
                                         'specifying the items type',
                                         path)
        # visit each item schema and use it to extend current elasticsearch
        # mapping
        path += '/items'
        if isinstance(items, list):
            index = 0
            for item in items:
                __gen_type_properties(item, path + '[' + str(index) + ']',
                                      resolver, config, es_mapping)
                index += 1
            return es_mapping
        else:
            # visit items' schema and use it to extend current elasticsearch
            # mapping
            return __gen_type_properties(items, path, resolver, config,
                                         es_mapping)

    # find the corresponding elasticsearch type
    if json_type == 'object':
        es_type = 'object'
    else:
        es_type, es_type_props = config.get_es_type(json_type,
                                                    json_schema.get('format'))

    # if current elasticsearch mapping's type is already known, the new one and
    # the old should match
    if 'type' in es_mapping or 'properties' in es_mapping:
        # 'properties' is set either when the elasticsearch type is 'object' or
        # for root types
        old_es_type = ('object' if 'properties' in es_mapping
                       else es_mapping['type'])
        if old_es_type != es_type:
            # elasticsearch root type mapping has no "type" property
            if 'properties' in es_mapping and 'type' not in es_mapping:
                raise JsonSchemaSupportError('Root schema type can ' +
                                             'only be "object".', path)
            else:
                raise JsonSchemaSupportError('Redefinition of field ' +
                                             'with another type is not ' +
                                             'supported.', path)

    # add the type to the elasticsearch mapping if it is not a root type
    if 'properties' not in es_mapping:
        es_mapping['type'] = es_type

    if es_type == 'object':
        es_properties = es_mapping.get('properties')
        if not es_properties:
            es_properties = {}
            es_mapping['properties'] = es_properties
        # build the elasticsearch mapping corresponding to each json schema
        # property
        for prop, prop_schema in json_schema['properties'].iteritems():
            es_properties[prop] = __gen_type_properties(prop_schema,
                                                        path + '/' + prop,
                                                        resolver, config,
                                                        es_properties.get(prop))
        # visit the dependencies defining additional properties
        if 'dependencies' in json_schema:
            deps_path = path + '/dependencies'
            for prop, deps in json_schema['dependencies'].iteritems():
                # if this is a "schema dependency", extend our current es
                # mapping with it
                if isinstance(deps, dict):
                    __gen_type_properties(deps, deps_path + '[' + prop + ']',
                                          resolver, config, es_mapping)
    else:
        es_mapping['type'] = es_type
        if es_type_props:
            for type_prop, type_prop_value in es_type_props.iteritems():
                es_mapping[type_prop] = type_prop_value

    # pop the current jsonschema context
    if has_scope:
        resolver.pop_scope()

    return es_mapping
