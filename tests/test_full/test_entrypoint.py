"""
Test optimisation chain
"""
from os.path import exists, join

from o2tuner.run import run


class AttrHolder:  # pylint: disable=(too-few-public-methods
    """
    To emulate what is done from argparse
    """
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_entrypoint(needs_sqlite, test_source_dir):  # pylint: disable=unused-argument
    """
    Simple optimisation using SQLite storage
    """
    config = join(test_source_dir, "config.yaml")
    assert exists(config)
    assert run(AttrHolder(config=config, work_dir="./", script_dir=None, stages=None)) == 0
