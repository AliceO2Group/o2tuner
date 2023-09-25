"""
Optimise hook, wrapping parallelisation
"""

from time import sleep
from math import floor
from multiprocessing import Process
from multiprocessing import set_start_method as mp_set_start_method
import functools

from o2tuner.io import make_dir, parse_yaml
from o2tuner.backends import OptunaHandler
from o2tuner.sampler import construct_sampler
from o2tuner.inspector import O2TunerInspector
from o2tuner.exception import O2TunerStopOptimisation
from o2tuner.system import kill_recursive
from o2tuner.log import get_logger, log_on_worker

# Do this to run via fork by default on latest iOS
mp_set_start_method("fork")

LOG = get_logger()


def optimise_run(objective, optuna_storage_config, sampler_config, n_trials, work_dir, user_config, in_memory, worker_id):
    """
    Run one of those per job
    """
    log_on_worker(worker_id)
    handler = OptunaHandler(optuna_storage_config.get("name", None), optuna_storage_config.get("storage", None), work_dir, user_config, in_memory)
    handler.set_objective(objective)
    handler.set_sampler(construct_sampler(sampler_config))
    handler.initialise(n_trials)
    handler.optimise()
    handler.finalise()
    return 0


def shutdown_optimisation(procs):
    """
    Helper to shutdown all current optimisation processes
    """
    LOG.info("Please wait until the optimisation is shut down...")
    for proc in procs:
        # give a timeout and the chance for the processes to terminate themselves
        kill_recursive(proc, 10)


def prepare_optimisation(optuna_config, work_dir="o2tuner_optimise"):
    """
    Prepare optimisation

    * create work_fir
    * check if storage run is possible (if requested)
    * adjust number of jobs if only a small number of trials

    dictionary optuna_config is modified inline
    """

    # read in the configurations, if string, assume to parse a YAML, otherwise it is assumed to be a dictionary
    if isinstance(optuna_config, str):
        optuna_config = parse_yaml(optuna_config)

    trials = optuna_config.get("trials", 100)
    jobs = optuna_config.get("jobs", 1)

    if trials < jobs:
        LOG.warning("Attempt to do %d trials, hence reducing the number of jobs from %d to %d", trials, jobs, trials)
        optuna_config["jobs"] = trials

    # investigate storage properties
    optuna_storage_config = optuna_config.get("study", {})

    # first, see what we got
    study_name = optuna_storage_config.get("name", "o2tuner_study")
    storage = optuna_storage_config.get("storage", None)

    if not storage:
        jobs = 1

    trials_list = floor(trials / jobs)
    trials_list = [trials_list] * jobs
    # add the left-over trials as equally as possible
    for i in range(trials - sum(trials_list)):
        trials_list[i] += 1

    LOG.info("Number of jobs: %d\nNumber of trials: %d", jobs, trials)

    make_dir(work_dir)

    return trials_list, study_name, storage


def optimise(objective, optuna_config, *, work_dir="o2tuner_optimise", user_config=None):
    """
    This is the entry point function for all optimisation runs

    args and kwargs will be forwarded to the objective function
    """

    trials_list, study_name, storage = prepare_optimisation(optuna_config, work_dir)
    if study_name is None:
        # that is a sign that the preparation went wrong
        return False

    # storage might be None at this point
    optuna_storage_config = {"name": study_name, "storage": storage}

    procs = []
    keep_running = True
    for worker_id, trial in enumerate(trials_list):
        try:
            procs.append(Process(target=optimise_run,
                                 args=(objective, optuna_storage_config, optuna_config.get("sampler", None),
                                       trial, work_dir, user_config, not storage, worker_id)))
            procs[-1].start()
            # just so that we do not immediately access the same storage, it might be created by the first process
            sleep(5)
        except O2TunerStopOptimisation:
            shutdown_optimisation(procs)
            keep_running = False
            break

    while keep_running:
        try:
            is_alive = any(p.is_alive() for p in procs)
            if not is_alive:
                break
        except O2TunerStopOptimisation:
            shutdown_optimisation(procs)
            break

    LOG.info("Finalise current optimisation run, please wait...")
    insp = O2TunerInspector()
    insp.load(optuna_config, work_dir)
    insp.write_summary()
    return True


def needs_cwd(func):
    """
    Decorator to be used for objective functions to indicate whether they need a dedicated directory to run in
    """
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        return func(*args, **kwargs)
    decorator.needs_cwd = True
    return decorator
