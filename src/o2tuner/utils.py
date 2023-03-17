"""
Common helper functionality
"""
import sys

from o2tuner.log import get_logger

LOG = get_logger()


def annotate_trial(trial, key, value):
    """
    Annotate a trial object with user key-value pair
    """
    user_attributes = trial.user_attrs

    if key in user_attributes:
        LOG.error("This trial has annotation %s already", key)
        sys.exit(1)

    trial.set_user_attr(key, value)
