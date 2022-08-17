"""
Common helper functionality
"""
import sys


def annotate_trial(trial, key, value):
    """
    Annotate a trial object with user key-value pair
    """
    user_attributes = trial.user_attrs

    if key in user_attributes:
        print(f"ERROR: This trial has annotation {key} already")
        sys.exit(1)

    trial.set_user_attr(key, value)
