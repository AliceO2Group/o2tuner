"""
Module used to test if installation is successful
"""


import o2tuner


def run_entrypoint():
    """
    Test the entrypoint
    """
    o2tuner.entrypoint()
    return 0


def test_run_entrypoint():
    """
    Ensure all run is performed
    """
    assert run_entrypoint() == 0
