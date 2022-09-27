"""
Optimise hook, wrapping parallelisation
"""

from time import sleep
from math import floor
from multiprocessing import Process
import functools

from o2tuner.io import make_dir, parse_yaml
from o2tuner.backends import OptunaHandler
from o2tuner.sampler import construct_sampler
from o2tuner.log import Log

LOG = Log()


def optimise_run(objective, optuna_storage_config, sampler, n_trials, work_dir, user_config, run_serial):
    """
    Run one of those per job
    """
    handler = OptunaHandler(optuna_storage_config.get("name", None), optuna_storage_config.get("storage", None), work_dir, user_config, run_serial)
    handler.initialise(n_trials)
    handler.set_objective(objective)
    handler.set_sampler(sampler)
    handler.optimise()
    handler.finalise()
    return 0


def optimise(objective, optuna_config, *, work_dir="o2tuner_optimise", user_config=None):
    """
    This is the entry point function for all optimisation runs

    args and kwargs will be forwarded to the objective function
    """

    # read in the configurations, if string, assume to parse a YAML, otherwise it is assumed to be a dictionary
    if isinstance(optuna_config, str):
        optuna_config = parse_yaml(optuna_config)

    trials = optuna_config.get("trials", 100)
    jobs = optuna_config.get("jobs", 1)

    # investigate storage properties
    optuna_storage_config = optuna_config.get("study", {})

    run_serial = False
    if not optuna_storage_config.get("name", None) or not optuna_storage_config.get("storage", None):
        # we reduce the number of jobs to 1. Either missing the table name or the storage path will anyway always lead to a new study
        LOG.info("No storage provided, running only one job.")
        run_serial = True
        jobs = 1

    if trials < jobs:
        LOG.info(f"Attempt to do {trials} trials, hence reducing the number of jobs from {jobs} to {trials}")
        jobs = trials

    trials_list = floor(trials / jobs)
    trials_list = [trials_list] * jobs
    # add the left-over trials simply to the last job for now
    trials_list[-1] += trials - sum(trials_list)

    LOG.info(f"Number of jobs: {jobs}\nNumber of trials: {trials}")

    sampler = construct_sampler(optuna_config.get("sampler", None))

    make_dir(work_dir)

    procs = []
    for trial in trials_list:
        procs.append(Process(target=optimise_run, args=(objective, optuna_storage_config, sampler, trial, work_dir, user_config, run_serial)))
        procs[-1].start()
        sleep(5)

    while True:
        is_alive = any(p.is_alive() for p in procs)
        if not is_alive:
            break
        # We assume here that the optimisation might take some time, so we can sleep for a bit
        sleep(10)
    return True


def needs_cwd(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        return func(*args, **kwargs)
    decorator.needs_cwd = True
    return decorator
