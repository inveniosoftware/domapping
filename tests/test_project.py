# SPDX-FileCopyrightText: 2015, 2016 CERN.
# SPDX-License-Identifier: MIT

"""Test project properties."""


def test_version():
    """Test version import."""
    from domapping import __version__

    assert __version__
