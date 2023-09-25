"""
Mainstream and custom backends should be placed here
"""
import sys
from time import time
from os import getcwd, chdir
from os.path import join
from inspect import signature
from copy import deepcopy
import pickle
# import needed to ensure sanity of storage
from sqlalchemy.exc import NoSuchModuleError

import optuna

from o2tuner.io import make_dir, exists_file
from o2tuner.utils import annotate_trial
from o2tuner.log import get_logger
from o2tuner.exception import O2TunerStopOptimisation

LOG = get_logger()


def make_trial_directory(trial):
    """
    Make a directory and attach to trial object as user attribute
    """
    user_attributes = trial.user_attrs
    if "cwd" in user_attributes:
        LOG.error("This trial has already a directory attached: %s", user_attributes["cwd"])
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


def adjust_storage_url(storage_url, workdir="./"):
    """
    From the full storage path, try to extract the identifier for what to be used
    """
    # check if there is a known identifier
    storage_prefixes = ["sqlite:///", "mysql:///"]

    for prefix in storage_prefixes:
        if storage_url.find(prefix) == 0:
            if prefix == "sqlite:///":
                # in case of SQLite, the file could be requested to be stored under an absolute or relative path
                # Do nothing for other storage URLs
                path = storage_url[len(prefix):]
                if path[0] != "/":
                    # if not an absolute path, put the working directory in between
                    storage_url = prefix + join(workdir, path)
            return storage_url

    LOG.warning("Unknown storage identifier in URL %s, might fail", storage_url)

    return storage_url


def get_default_storage_url(study_name="o2tuner_study"):
    """
    Construct a default storage path
    """
    return f"sqlite:///{study_name}.db"


def create_storage(storage, workdir):
    """
    Make sure the path is either absolute path or relative to the specified workdir.
    Take care of storage identifier. Right now check for MySQL and SQLite.
    """

    # default arguments which we will use
    # for now, use a high timeout so we don't fail if another process is currently using the storage backend
    engine_kwargs = {"connect_args": {"timeout": 100}}

    if isinstance(storage, str):
        # simply treat this as the storage url
        url = storage
    else:
        # first pop the url...
        url = storage.pop("url", None)
        if not url:
            LOG.error("No storage URL found in configuration")
            return None
        if storage:
            # ...then check, if there is more in the dictionary; if so, use it
            engine_kwargs = storage

    # check if there is a known identifier
    url = adjust_storage_url(url, workdir)
    try:
        storage = optuna.storages.RDBStorage(url=url, engine_kwargs=engine_kwargs)
        return storage
    except (ImportError, NoSuchModuleError) as import_error:
        LOG.error(import_error)
    return None


def load_or_create_study_from_storage(study_name, storage, sampler=None, create_if_not_exists=True):
    """
    Load or create from DB
    """
    try:
        study = optuna.load_study(study_name=study_name, storage=storage, sampler=sampler)
        LOG.debug("Loading existing study %s from storage %s", study_name, storage.url)
        return study
    except KeyError:
        if create_if_not_exists:
            study = optuna.create_study(study_name=study_name, storage=storage, sampler=sampler)
            LOG.debug("Creating new study %s at storage %s", study_name, storage.url)
            return study
        LOG.error("Study %s does not exist but was supposed to be loaded.", study_name)

    return None


def load_or_create_study_in_memory(study_name, workdir, sampler=None, create_if_not_exists=True):
    """
    Try to see if there is a study saved here

    (Pickling is unsafe, we should try to find another way eventually)
    """
    file_name = join(workdir, f"{study_name}.pkl")
    if not exists_file(file_name) and not create_if_not_exists:
        LOG.error("Study %s does not exist but was supposed to be loaded.", study_name)
        return None
    if exists_file(file_name):
        # in this case, load
        with open(file_name, "rb") as save_file:
            LOG.debug("Loading existing study %s from file %s", study_name, file_name)
            return pickle.load(save_file)

    LOG.debug("Creating new in-memory study %s", study_name)

    return optuna.create_study(study_name=study_name, sampler=sampler)


def load_or_create_study(study_name, storage_config=None, sampler=None, workdir="./", create_if_not_exists=True):
    """
    Helper to load or create a study
    Returns tuple of whether it can run via storage and the created/loaded optuna.study.Study object.

    Use following logic:

    First, check if study exists for provided name and storage. If not, try to create a new one.
    If that fails as well (probably at that point due to missing dependencies), attempt an in-memory
    optimisation.

    If anything before failed but a working directory and a study name is provided, check for a pickle
    file in the given directory with <study_name>.pkl. If found, tru to load.
    If also this does not exist, create a new in-memory study.
    """
    if storage_config:
        storage = create_storage(storage_config, workdir)
        if not storage:
            LOG.error("Storage for study %s cannot be established, please check the storage configuration.", study_name)
            sys.exit(1)
        # Although optuna would come up with a unique name when study_name is None,
        # we force a name to be given by the user for those cases
        study = load_or_create_study_from_storage(study_name, storage, sampler, create_if_not_exists)
        if not study:
            LOG.error("Study %s cannot be loaded.", study_name)
            sys.exit(1)
        return True, study

    study = load_or_create_study_in_memory(study_name, workdir, sampler, create_if_not_exists)

    if not study:
        LOG.error("Cannot create in-memory study %s", study_name)
        sys.exit(1)

    # simple in-memory
    return False, study


def pickle_study(study, workdir="./"):
    """
    Wrapper to pickle a study
    Pickling could be seen as being unsafe, we should try to find another way eventually
    """
    file_name = join(workdir, f"{study.study_name}.pkl")
    with open(file_name, "wb") as save_file:
        pickle.dump(study, save_file)
    LOG.info("Pickled the study %s at %s.", study.study_name, file_name)
    return file_name


class OptunaHandler:
    """
    Handler based on Optuna backend
    """

    def __init__(self, db_study_name=None, db_storage=None, workdir=None, user_config=None, in_memory=False) -> None:
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
        # Flag to indicate if this is an in-memory run
        self.in_memory = in_memory

    def finalise_configuration(self):
        """
        Pass in some O2Tuner related configurations that might be interesting for the user
        """
        sampler = self._study.sampler
        if isinstance(sampler, optuna.samplers.GridSampler):
            self.user_config["O2TUNER_GridSampler_SearchSpace"] = deepcopy(sampler._search_space)  # pylint: disable=protected-access

    def objective_cwd_wrapper(self, trial):
        """
        If this trial needs a dedicated cwd, create it, change into it, run the objective and go back
        """
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
        """
        Initialise with number of trials to be done
        """
        self._n_trials = n_trials
        has_db_access, self._study = load_or_create_study(self.db_study_name, self.db_storage, self._sampler, self.workdir)
        # Overwrite in case no DB access but a parallel execution was desired before
        self.in_memory = not has_db_access

        if self.workdir:
            self._study.set_user_attr("cwd", self.workdir)

    def optimise(self):
        """
        Now this takes the appropriately wrapped objective of the user and passes it finally to optuna.
        """
        if not self._n_trials or self._n_trials < 0 or not self._objective:
            LOG.error("Not initialised: Number of trials and objective function need to be set")
            return
        # add some special configuration
        self.finalise_configuration()
        try:
            self._study.optimize(self.objective_cwd_wrapper, n_trials=self._n_trials)
        except O2TunerStopOptimisation:
            # give it a chance to shutdown by itself before it will be removed by the parent process
            pass

    def finalise(self):
        """
        Finalise, right now only pickle if it was an in-memory run
        """
        if self.in_memory and self.workdir:
            # Save the study if this is in-memory
            pickle_study(self._study, self.workdir)

    def set_objective(self, objective):
        """
        Set the objective and wrap it if necessary.

        Wrapping:
        First, figure out if the function was decorated to indicate whether or not each trial needs a dedicated cwd to run in.
        Second, check the function signature. A user might or might not provide an argument to pass the static config.
        """
        sig = signature(objective)
        n_params = len(sig.parameters)
        if hasattr(objective, "needs_cwd"):
            self._needs_cwd_per_trial = True
        if n_params > 2 or not n_params:
            LOG.error("Invalid signature of objective function. Need either 1 argument (only trial obj) or 2 arguments (trial object + user_config)")
            sys.exit(1)
        if n_params == 1:
            self._objective = objective
        else:
            # Additionally pass the static user config
            if not self.user_config:
                LOG.warning("The objective takes a config argument, however, your config is empty")
            self._objective = lambda trial: objective(trial, self.user_config)

    def set_sampler(self, sampler):
        """
        Set the sampler from the outside
        """
        self._sampler = sampler
