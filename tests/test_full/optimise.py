"""
To test the full o2tuner chain
"""

from o2tuner.utils import annotate_trial


def objective(trial, config):
    """
    A dummy objective
    """
    x = trial.suggest_float("x", -10, 10)
    y = trial.suggest_float("y", -10, 10)
    annotate_trial(trial, "sum", x + y)
    annotate_trial(trial, "some_key", config["some_key"])
    return (x - 2)**2 + (y - 3)**2
