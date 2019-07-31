# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2019 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Exceptions used in this package."""


class JsonSchemaSupportError(Exception):
    """Exception raised when a json schema is not supported by a function."""

    def __init__(self, message, path, *args, **kwargs):
        """Constructor.

        :param message: error message
        :param path: path of the failing file
        """
        super(JsonSchemaSupportError, self).__init__(*args, **kwargs)
        self.message = message
        self.path = path

    def __str__(self):
        """Return the formatted error message string."""
        return 'ERROR {0} IN {1}'.format(self.message, self.path)


class UnknownFieldTypeError(Exception):
    """Exception raised when a json schema field type cannot be guessed."""

    def __init__(self, message, path, *args, **kwargs):
        """Constructor.

        :param message: error message
        :param path: path of the failing file
        """
        super(UnknownFieldTypeError, self).__init__(*args, **kwargs)
        self.message = message
        self.path = path

    def __str__(self):
        """Return the formatted error message string."""
        return 'ERROR {0} IN {1}'.format(self.message, self.path)
