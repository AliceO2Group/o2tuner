"""
Common helper functionality
"""
import sys

from o2tuner.log import Log

LOG = Log()


def annotate_trial(trial, key, value):
    """
    Annotate a trial object with user key-value pair
    """
    user_attributes = trial.user_attrs

    if key in user_attributes:
        LOG.error(f"This trial has annotation {key} already")
        sys.exit(1)

    trial.set_user_attr(key, value)
