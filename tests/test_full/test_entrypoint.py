"""
Test optimisation chain
"""
from os.path import exists, join

from o2tuner.run import run
from o2tuner.bookkeeping import AttrHolder


def test_entrypoint_full_config(needs_sqlite, test_source_dir):  # pylint: disable=unused-argument
    """
    Simple optimisation using SQLite storage, use full optimisation config
    """
    config = join(test_source_dir, "config_full.yaml")
    assert exists(config)
    assert run(AttrHolder(config=config, work_dir="./", script_dir=None, stages=None)) == 0


def test_entrypoint_minimal_config(needs_sqlite, test_source_dir):  # pylint: disable=unused-argument
    """
    Simple optimisation using SQLite storage, use minimal optimisation
    """
    config = join(test_source_dir, "config_minimal.yaml")
    assert exists(config)
    assert run(AttrHolder(config=config, work_dir="./", script_dir=None, stages=None)) == 0
