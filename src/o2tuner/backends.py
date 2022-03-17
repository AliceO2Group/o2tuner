"""
Mainstream and custom backends should be placed here
"""


import optuna


class OptunaHandler(object):
    """
    Handler based on Optuna backend
    """

    def __init__(self) -> None:
        """
        Constructor
        """
        self._objective = None
        self._study = None
        self._n_trials = 100

    def initialise(self, n_trials=100):
        self._n_trials = n_trials
        self._study = optuna.create_study()

    def optimise(self):
        self._study.optimize(self._objective, n_trials=self._n_trials)

    def set_objective(self, objective):
        self._objective = objective
