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

"""Elastic Search integration. mapping funtion."""

import jsonschema
from six import integer_types, iteritems, string_types

from .errors import JsonSchemaSupportError, UnknownFieldTypeError


class ElasticMappingGeneratorConfig(object):
    """Configuration used during elasticsearch mapping generation."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(ElasticMappingGeneratorConfig, self).__init__(*args, **kwargs)
        self.all_field = True
        """Enable/Disable "all" field generation in elasticsearch mappings."""
        self.date_detection = True
        """Enable/Disable date detection in elasticsearch mappings."""
        self.numeric_detection = True
        """Enable/Disable number detection in elasticsearch mappings."""
        self.date_format = None
        """Date format used in elasticsearch mappings."""
        # json type -> elasticsearch type
        # this contains the default string mapping when no format matches
        self._types_map = {
            'string': {'type': 'string'},
            'number': {'type': 'double'},
            'integer': {'type': 'integer'},
            'boolean': {'type': 'boolean'},
        }
        # json string formats -> elasticsearch type
        self._formats_map = {}

    def load(self, config):
        """Load a configuration dict, overriding current configuration.

        The configuration dict should be of the form:
        .. code-block:: python
            {
                # type mappings with parameters for py:meth:`map_type`
                'types': [{
                    'es_type': 'elasticsearch type',
                    'json_type': 'JSON Schema type',
                    'json_format': 'JSON Schema format',
                    'es_props': {
                        # additional elasticsearch properties
                    },
                }, ...],
                # override configuration properties
                'date_format': 'default date format',
                'all_field': True,
                'date_detection': True,
                'numeric_detection': True,
            }

        :param config: A configuration dict.
        """
        for type_config in config['types']:
            self.map_type(**type_config)
        if 'all_field' in config:
            self.all_field = config['all_field']
        if 'date_format' in config:
            self.date_format = config['date_format']
        if 'date_detection' in config:
            self.date_detection = config['date_detection']
        if 'numeric_detection' in config:
            self.numeric_detection = config['numeric_detection']

    def map_type(self, es_type, json_type, json_format=None, es_props=None):
        """Map a json schema type to an elasticsearch type.

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
            self._formats_map[json_format] = stored_mapping
        else:
            self._types_map[json_type] = stored_mapping
        return self

    def get_es_type(self, json_type, json_format=None):
        """Return the elasticsearch type matching the given json type.

        :param json_type: json type.
        :param json_format: json format (optional).
        """
        if (json_type == 'string' and json_format and
                json_format in self._formats_map):
            stored = self._formats_map.get(json_format)
        else:
            stored = self._types_map[json_type]
        props = stored.get('props') or {}
        if (stored['type'] == 'date' and 'format' not in props):
            props['format'] = self.date_format
        return (stored['type'], props)


def schema_to_mapping(json_schema, base_uri, context_schemas, config):
    """Generate an elasticsearch type properties' mapping from a json schema.

    It generates only the "type" and "properties" fields.

    :param json_schema: json schema used to generate the elasticsearch mapping
    :param base_uri: json path pointing to the given json_schema. Used for
    debug.
    :param context_schemas: dict of schema_id -> schema used to resolve
        references.
    :param config: configuration used to generate the elasticsearch mapping.
    """
    resolver = jsonschema.RefResolver(referrer=json_schema,
                                      store=context_schemas,
                                      base_uri=base_uri)
    return _gen_type_properties(json_schema, base_uri, resolver, config, {
        '_all': {'enable': config.all_field},
        'numeric_detection': config.numeric_detection,
        'date_detection': config.date_detection,
        # empty type mapping
        'properties': {},
    })


_collection_keys = frozenset(['allOf', 'anyOf', 'oneOf'])


def _gen_type_properties(json_schema, path, resolver, config, es_mapping):
    """Generate an elasticsearch type properties' mapping from a json schema.

    The mapping's type generation is recursive.
    It generates only the "type" and "properties" fields.

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

    def dict_search_and_retrieve(d, key=None):
        """Get the values associated to a specific key in nested dicts.

        :param d: Dictionnary to explore.
        :type d: dict
        :param key: key to look value for. If ``None``, it returns all values.
        :type key: str
        :return: A list containing the value associated to key.
        :rtype: list
        """
        for k in d.keys():
            if isinstance(d[k], dict):
                for val in dict_search_and_retrieve(d[k], key):
                    yield val
            else:
                if (key and k == key) or not key:
                    yield d[k]

    # resolve reference if there are any
    while '$ref' in json_schema:
        path = json_schema.get('$ref')
        json_schema = resolver.resolve(path)[1]

    if 'patternProperties' in json_schema:
        raise JsonSchemaSupportError('Schemas with patternProperties ' +
                                     'are not supported.', path)

    additionalPropertiesVals = dict_search_and_retrieve(json_schema,
                                                        'additionalProperties')

    # Check if we have any other value than False.
    # False means that no additionalProperties are allowed.
    # https://spacetelescope.github.io/
    # understanding-json-schema/reference/object.html#properties
    if any(additionalPropertiesVals):
        raise JsonSchemaSupportError('Schemas with ' +
                                     'additionalProperties are not ' +
                                     'supported.', path)

    if es_mapping is None:
        es_mapping = {}

    # if the schema is in fact a collection of schemas, merge them
    json_schema_keys = set(json_schema.keys())
    collection_intersect = json_schema_keys.intersection(_collection_keys)
    if collection_intersect:
        # we suppose the schema is valid and only one of the collection keys
        # is present
        collection_key = collection_intersect.pop()
        # visit each schema and use it to extend current elasticsearch
        # mapping
        path += '/' + collection_key
        index = 0
        for sub_schema in json_schema.get(collection_key):
            _gen_type_properties(sub_schema, path + '[' + str(index) + ']',
                                 resolver, config, es_mapping)
            index += 1
        return es_mapping

    # get json schema type
    json_type = json_schema.get('type')

    if not json_type:
        if 'properties' in json_schema:
            json_type = 'object'
        elif 'enum' in json_schema:
            json_type = _guess_enum_type(json_schema['enum'], path)
        else:
            raise UnknownFieldTypeError(
                'Schema field type cannot be guessed. Only fields with "type"'
                ' defined or with an "enum" array of strings are supported',
                path)

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
                _gen_type_properties(item, path + '[' + str(index) + ']',
                                     resolver, config, es_mapping)
                index += 1
            return es_mapping
        else:
            # visit items' schema and use it to extend current elasticsearch
            # mapping
            return _gen_type_properties(items, path, resolver, config,
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
        for prop, prop_schema in iteritems(json_schema['properties']):
            es_properties[prop] = _gen_type_properties(
                prop_schema,
                path + '/' + prop,
                resolver, config,
                es_properties.get(prop))
        # visit the dependencies defining additional properties
        if 'dependencies' in json_schema:
            deps_path = path + '/dependencies'
            for prop, deps in iteritems(json_schema['dependencies']):
                # if this is a "schema dependency", extend our current es
                # mapping with it
                if isinstance(deps, dict):
                    _gen_type_properties(deps, deps_path + '[' + prop + ']',
                                         resolver, config, es_mapping)
    else:
        es_mapping['type'] = es_type
        if es_type_props:
            for type_prop, type_prop_value in iteritems(es_type_props):
                es_mapping[type_prop] = type_prop_value

    # pop the current jsonschema context
    if has_scope:
        resolver.pop_scope()

    return es_mapping


def _guess_enum_type(enum_array, path):
    """Try to guess what a field's type is from the provided enum array.

    Only string values are supported for the time being.
    """
    if all(isinstance(value, string_types) for value in enum_array):
        return 'string'
    elif all(isinstance(value, integer_types) for value in enum_array):
        return 'number'
    else:
        raise UnknownFieldTypeError(
            'Mixed types in "{}" enum are not supported. Schema field type'
            ' cannot be guessed from enum. Only "string" or "integer"'
            ' values are accepted when "type" is not defined.'.format(
                enum_array
            ), path)


def clean_mapping(mapping):
    """Recursively remove all fields set to None in a dict and child dicts.

    This enables to override a field in a mapping's jinja template by just
    adding it again with a null value.
    """
    return {key: (value if not isinstance(value, dict)
                  else clean_mapping(value))
            for (key, value) in iteritems(mapping) if value is not None}
