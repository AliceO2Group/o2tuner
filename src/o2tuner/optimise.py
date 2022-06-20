"""
Optimise hook, wrapping parallelisation
"""

from time import sleep
from math import floor
from multiprocessing import Process

from o2tuner.io import make_dir, parse_yaml
from o2tuner.backends import OptunaHandler
from o2tuner.sampler import construct_sampler


def optimise_run(objective, optuna_storage_config, sampler, n_trials, workdir, user_config):
    """
    Run one of those per job
    """
    handler = OptunaHandler(optuna_storage_config.get("name", None), optuna_storage_config.get("storage", None), workdir, user_config)
    handler.initialise(n_trials)
    handler.set_objective(objective)
    handler.set_sampler(sampler)
    handler.optimise()
    return 0


def optimise(objective, optuna_config, *, user_config=None, init_func=None):
    """
    This is the entry point function for all optimisation runs

    args and kwargs will be forwarded to the objective function
    """

    # read in the configurations
    optuna_config = parse_yaml(optuna_config)

    trials = optuna_config.get("trials", 100)
    jobs = optuna_config.get("jobs", 1)

    # investigate storage properties
    optuna_storage_config = optuna_config.get("study", {})

    if not optuna_storage_config.get("name", None) or not optuna_storage_config.get("storage", None):
        # we reduce the number of jobs to 1. Either missing the table name or the storage path will anyway always lead to a new study
        print("WARNING: No storage provided, running only one job.")
        jobs = 1

    trials_list = floor(trials / jobs)
    trials_list = [trials_list] * jobs
    # add the left-over trials simply to the last job for now
    trials_list[-1] += trials - sum(trials_list)

    # Digest user configuration and call an initialisation if requested
    user_config = parse_yaml(user_config) if user_config else None
    if init_func:
        init_func(user_config)

    print(f"Number of jobs: {jobs}\nNumber of trials: {trials}")

    sampler = construct_sampler(optuna_config.get("sampler", None))

    workdir = optuna_config.get("workdir", "o2tuner_optimise")
    make_dir(workdir)

    procs = []
    for trial in trials_list:
        procs.append(Process(target=optimise_run, args=(objective, optuna_storage_config, sampler, trial, workdir, user_config)))
        procs[-1].start()
        sleep(5)

    while True:
        is_alive = any(p.is_alive() for p in procs)
        if not is_alive:
            break
        # We assume here that the optimisation might take some time, so we can sleep for a bit
        sleep(10)
    return 0
