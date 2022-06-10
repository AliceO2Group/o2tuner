"""
Mainstream and custom backends should be placed here
"""
import sys
from inspect import signature

from o2tuner.utils import load_or_create_study


class OptunaHandler(object):
    """
    Handler based on Optuna backend
    """

    def __init__(self, db_study_name=None, db_storage=None, workdir=None, user_config=None) -> None:
        """
        Constructor
        """
        # user objective function
        self._objective = None
        # chosen sampler (can be None, optuna will use TPE then)
        self._sampler = None
        # our study object
        self._study = None
        # number of trials to be done in given study
        self._n_trials = None
        # name of study (in database)
        self.db_study_name = db_study_name
        # database storage
        self.db_storage = db_storage
        # working directory (if any)
        self.workdir = workdir
        # optional user configuration that will be passed down to each call of the objective
        self.user_config = user_config

    def initialise(self, n_trials=100):
        self._n_trials = n_trials
        self._study = load_or_create_study(self.db_study_name, self.db_storage, self._sampler)

        if self.workdir:
            self._study.set_user_attr("cwd", self.workdir)

    def optimise(self):
        if not self._n_trials or not self._objective:
            print("ERROR: Not initialised: Number of trials and objective function need to be set")
            return
        self._study.optimize(self._objective, n_trials=self._n_trials)

    def set_objective(self, objective):
        sig = signature(objective)
        n_params = len(sig.parameters)
        if n_params > 2 or not n_params:
            print("Invalid signature of objective funtion. Need either 1 argument (only trial object) or 2 arguments (trial object and user_config)")
            sys.exit(1)
        if n_params == 1:
            self._objective = objective
        else:
            # Additionally pass the user config
            self._objective = lambda trial: objective(trial, self.user_config)

    def set_sampler(self, sampler):
        self._sampler = sampler
