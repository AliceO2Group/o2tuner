"""
Test creating and loading of study
"""
from os.path import exists

import optuna

from o2tuner.backends import load_or_create_study, pickle_study


def test_inmemory_creation_and_pickle():
    """
    Test in-memory creation of study and make sure it can be pickled
    """
    study_name = "o2tuner_test_study"
    has_storage, study = load_or_create_study(study_name)
    assert not has_storage
    assert isinstance(study, optuna.study.Study)
    assert study.study_name == study_name
    filename = pickle_study(study, "./")
    assert exists(filename)


def test_storage_creation(needs_sqlite):  # pylint: disable=unused-argument
    """
    Test storage creation of study
    """
    study_name = "o2tuner_test_study"
    storage = "sqlite:///o2tuner_test_study.db"
    has_storage, study = load_or_create_study(study_name, storage)
    assert has_storage
    assert isinstance(study, optuna.study.Study)
