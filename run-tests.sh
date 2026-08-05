#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2015, 2016 CERN.
# SPDX-License-Identifier: MIT

pydocstyle domapping && \
isort -rc -c -df **/*.py && \
sphinx-build -qnNW docs docs/_build/html && \
python setup.py test && \
sphinx-build -qnNW -b doctest docs docs/_build/doctest
