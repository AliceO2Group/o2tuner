"""
Module used to test if installation is successful
"""

import sys
from unittest import mock
import o2tuner


def run_entrypoint():
    """
    Test the entrypoint
    """
    with mock.patch.object(sys, "argv", ["run"]):
        o2tuner.entrypoint()
        return 0
    return 1


def test_entrypoint():
    """
    Ensure all run is performed
    """
    val = run_entrypoint()
    print(val)
    assert val == 0
