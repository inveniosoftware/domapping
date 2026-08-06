#!/usr/bin/env sh
# SPDX-FileCopyrightText: 2015, 2016 CERN.
# SPDX-License-Identifier: MIT

pydocstyle domapping && \
isort -rc -c -df **/*.py && \
python -m sphinx.cmd.build -qnN docs docs/_build/html && \
pytest && \
python -m sphinx.cmd.build -qnN -b doctest docs docs/_build/doctest
