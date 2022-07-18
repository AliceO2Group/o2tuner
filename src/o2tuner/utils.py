"""
Common helper functionality
"""
import sys
from time import time
from os.path import join

import optuna

from o2tuner.io import make_dir


def annotate_trial(trial, key, value):
    """
    Annotate a trial object with user key-value pair
    """
    user_attributes = trial.user_attrs

    if key in user_attributes:
        print(f"ERROR: This trial has annotation {key} already")
        sys.exit(1)

    trial.set_user_attr(key, value)


def make_trial_directory(trial):
    """
    Make a directory and attach to trial object as user attribute
    """
    user_attributes = trial.user_attrs
    if "cwd" in user_attributes:
        print(f"ERROR: This trial has already a directory attached: {user_attributes['cwd']}")
        sys.exit(1)
    top_dir = trial.study.user_attrs["cwd"]
    timestamp = str(int(time() * 1000000))
    cwd = join(top_dir, timestamp)
    make_dir(cwd)
    annotate_trial(trial, "cwd", cwd)
    return cwd


def load_or_create_study(study_name=None, storage=None, sampler=None):
    """
    Helper to load or create a study
    """
    if study_name and storage:
        # there is a database we can connect to for multiprocessing
        # Although optuna would come up with a unique name when study_name is None,
        # we force a name to be given by the user for those cases
        try:
            study = optuna.load_study(study_name=study_name, storage=storage, sampler=sampler)
            print(f"Loading existing study {study_name} from storage {storage}")
        except KeyError:
            study = optuna.create_study(study_name=study_name, storage=storage, sampler=sampler)
            print(f"Creating new study {study_name} at storage {storage}")
        return study
    # This is a "one-time" in-memory study so we don't care so much for the name honestly, could be None
    return optuna.create_study(study_name=study_name, sampler=sampler)
