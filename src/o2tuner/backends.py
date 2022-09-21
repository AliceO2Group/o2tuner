"""
Mainstream and custom backends should be placed here
"""
import sys
from time import time
from os import getcwd, chdir
from os.path import join
from inspect import signature
import pickle

import optuna

from o2tuner.io import make_dir, exists_file
from o2tuner.utils import annotate_trial
from o2tuner.log import Log

LOG = Log()


def make_trial_directory(trial):
    """
    Make a directory and attach to trial object as user attribute
    """
    user_attributes = trial.user_attrs
    if "cwd" in user_attributes:
        LOG.error(f"This trial has already a directory attached: {user_attributes['cwd']}")
        sys.exit(1)
    if "cwd" not in trial.study.user_attrs:
        LOG.error("This optimisation was not configured to run inside a directory. Please define a working directory.")
        sys.exit(1)
    top_dir = trial.study.user_attrs["cwd"]
    timestamp = str(int(time() * 1000000))
    cwd = join(top_dir, timestamp)
    make_dir(cwd)
    annotate_trial(trial, "cwd", cwd)
    return cwd


def adjust_path_sqlite(storage, workdir):
    """
    Make sure the path for SQLite is located either at an absolute path or relative to the specified workdir
    """
    if not storage:
        return None
    if storage.find("sqlite:///") != 0 or not workdir:
        return storage
    path = storage[10:]
    if path[0] == "/":
        # Absolute path
        return storage
    return "sqlite:///" + join(workdir, path)


def load_or_create_study(study_name=None, storage=None, sampler=None, workdir=None):
    """
    Helper to load or create a study
    Returns tuple of whether it can run via DB interface and optuna.study.study.Study
    """
    storage = adjust_path_sqlite(storage, workdir)
    if study_name and storage:
        # there is a database we can connect to for multiprocessing
        # Although optuna would come up with a unique name when study_name is None,
        # we force a name to be given by the user for those cases
        try:
            study = optuna.load_study(study_name=study_name, storage=storage, sampler=sampler)
            LOG.info(f"Loading existing study {study_name} from storage {storage}")
            return True, study
        except KeyError:
            study = optuna.create_study(study_name=study_name, storage=storage, sampler=sampler)
            LOG.info(f"Creating new study {study_name} at storage {storage}")
            return True, study
        except ImportError as exc:
            # Probably cannot import MySQL stuff
            LOG.info("Probably cannot import what is needed for database access. Will try to attempt a serial run.")
            LOG.info(exc)

    if study_name and workdir:
        # Try to see if there is a study saved here
        # Pickling is unsafe, we should try to find another way eventually
        file_name = join(workdir, f"{study_name}.pkl")
        if exists_file(file_name):
            with open(file_name, "rb") as save_file:
                LOG.info(f"Loading existing study {study_name} from file {file_name}")
                return False, pickle.load(save_file)

    return False, optuna.create_study(study_name=study_name, sampler=sampler)


def save_study(study, workdir):
    """
    Wrapper to pickle a study
    Pickling is unsafe, we should try to find another way eventually
    """
    if workdir:
        file_name = join(workdir, f"{study.study_name}.pkl")
        with open(file_name, "wb") as save_file:
            pickle.dump(study, save_file)


class OptunaHandler(object):
    """
    Handler based on Optuna backend
    """

    def __init__(self, db_study_name=None, db_storage=None, workdir=None, user_config=None, run_serial=False) -> None:
        """
        Constructor
        """
        # user objective function
        self._objective = None
        # Flag whether we need a dedicated cwd per trial
        self._needs_cwd_per_trial = False
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
        # Flag to indicate if this is a serial run
        self.run_serial = run_serial

    def objective_wrapper(self, trial):
        cwd = None
        this_dir = getcwd()
        if self._needs_cwd_per_trial:
            cwd = make_trial_directory(trial)
        if cwd:
            chdir(cwd)
        ret = self._objective(trial)
        chdir(this_dir)
        return ret

    def initialise(self, n_trials=100):
        self._n_trials = n_trials
        has_db_access, self._study = load_or_create_study(self.db_study_name, self.db_storage, self._sampler, self.workdir)
        # Overwrite in case no DB access but a parallel execution was desired before
        self.run_serial = not has_db_access

        if self.workdir:
            self._study.set_user_attr("cwd", self.workdir)

    def optimise(self):
        if not self._n_trials or not self._objective:
            LOG.error("Not initialised: Number of trials and objective function need to be set")
            return
        self._study.optimize(self.objective_wrapper, n_trials=self._n_trials)

    def finalise(self):
        if self.run_serial and self.workdir:
            # Save the study if this is run serial and a workdir is given
            save_study(self._study, self.workdir)

    def set_objective(self, objective):
        sig = signature(objective)
        n_params = len(sig.parameters)
        if hasattr(objective, "needs_cwd"):
            self._needs_cwd_per_trial = True
        if n_params > 2 or not n_params:
            LOG.error("Invalid signature of objective funtion. Need either 1 argument (only trial obj) or 2 arguments (trial object + user_config)")
            sys.exit(1)
        if n_params == 1:
            self._objective = objective
        else:
            # Additionally pass the user config
            self._objective = lambda trial: objective(trial, self.user_config)

    def set_sampler(self, sampler):
        self._sampler = sampler
