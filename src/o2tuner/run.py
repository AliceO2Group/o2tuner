"""
Utility to run stages, bound to main entrypoint run action
"""
import sys
import argparse
from os.path import join, abspath, expanduser
from os import getcwd, chdir

from o2tuner.system import run_command, import_function_from_file
from o2tuner.optimise import optimise
from o2tuner.io import make_dir
from o2tuner.config import load_config, prepare_work_dir, get_stages_done, set_stage_done, set_work_dir, get_work_dir
from o2tuner.graph import create_graph_walker
from o2tuner.inspector import O2TunerInspector
from o2tuner.log import Log

OPTIMISATION_STAGE_FLAG = 0
EVALUATION_STAGE_FLAG = 1
USER_STAGE_FLAG = 2

LOG = Log()


def get_stage_work_dir(name, config):
    cwd_rel = config.get("cwd", name)
    return join(get_work_dir(), cwd_rel), cwd_rel


def get_optuna_config(name, config):
    optuna_config = {k: v for k, v in config.items() if k not in ("entrypoint", "objective", "script", "config")}
    if "study" not in optuna_config:
        optuna_config["study"] = {"name": name}
        return optuna_config
    if "name" not in optuna_config["study"]:
        optuna_config["study"]["name"] = name
    return optuna_config


def run_cmd_or_python(cwd, name, config):
    if "cmd" not in config and "python" not in config:
        LOG.error("Need either the cmd or python section in the config")
        return False
    if "python" in config:
        path = config["python"].get("file", None)
        entrypoint = config["python"].get("entrypoint", None)
        if not path or not entrypoint:
            LOG.error("Need path to python file and entrypoint function")
            return False
        user_config = config.get("config", {})
        # import function to be execuuted
        func = import_function_from_file(path, entrypoint)
        # cache current directory
        this_dir = getcwd()
        # change to this cwd and afterwards back
        chdir(cwd)
        if user_config:
            ret = func(user_config)
        else:
            ret = func()
        chdir(this_dir)
        return ret
    # We need to extract the return code here in a reasonable manner
    # It is not well defined to just get it via psutil.Process.wait() since it can happen
    # that the process is already done and return code can not even be found in the
    # system's process table anymore
    run_command(config["cmd"], cwd=cwd, log_file=config.get("log_file", f"{name}.log"), wait=True)
    return True


def run_optimisation(cwd, name, config):
    """
    Wrapper to run the optimisation.
    """
    func_name = config.get("entrypoint", config.get("objective", None))
    if not func_name or "file" not in config:
        LOG.error("Need path to python file and name of function entrypoint")
        return False
    func = import_function_from_file(config["file"], func_name)
    if not func:
        return False
    optuna_config = get_optuna_config(name, config)

    user_config = config.get("config", {})
    # cache current directory
    this_dir = getcwd()
    # change to this cwd and afterwards back
    chdir(cwd)
    ret = optimise(func, optuna_config, work_dir="./", user_config=user_config)
    chdir(this_dir)
    return ret


def run_inspector(cwd, config, stages_optimisation):
    """
    Wrapper to run the optimisation.
    """
    func_name = config.get("entrypoint", None)
    if not func_name or "file" not in config:
        LOG.error("Need path to python file and name of function entrypoint")
        return False
    func = import_function_from_file(config["file"], func_name)
    if not func:
        return False
    # which optimisations to load
    if "optimisations" not in config:
        LOG.error("Need key \"optimisations\" to know which optimisations to load")
        return False

    user_config = config.get("config", {})

    inspectors = []

    for optimisation in config["optimisations"]:
        if optimisation not in stages_optimisation:
            LOG.warning(f"Optimisation stage {optimisation} not defined, cannot construct inspector for that. Skip...")
            continue
        opt_config = stages_optimisation[optimisation]
        opt_cwd, _ = get_stage_work_dir(optimisation, opt_config)
        optuna_config = get_optuna_config(optimisation, opt_config)
        insp = O2TunerInspector()
        if not insp.load(optuna_config, opt_cwd, user_config):
            continue
        inspectors.append(insp)

    if not inspectors:
        LOG.warning("No O2TunerInspectors loaded, nothing to do")
        return False

    # cache current directory
    this_dir = getcwd()
    # change to this cwd and afterwards back
    chdir(cwd)
    ret = func(inspectors, user_config)
    chdir(this_dir)
    return ret


def run_stages(config, which_stages):  # noqa: C901 pylint: disable=too-many-branches
    """
    Run the stages defined in the config specified by the user
    Run all if nothing is specified
    """
    stages_user = config.get("stages_user", {})
    stages_optimisation = config.get("stages_optimisation", {})
    stages_evaluation = config.get("stages_evaluation", {})

    # Flag normal user stages with False to indicate that this is not an optimisation step
    stages = [(name, value, USER_STAGE_FLAG) for name, value in stages_user.items()]
    for name, value in stages_optimisation.items():
        # Instead, flag these stages with True to indicate these are optimisation steps
        stages.append((name, value, OPTIMISATION_STAGE_FLAG))
    for name, value in stages_evaluation.items():
        # Instead, flag these stages with True to indicate these are optimisation steps
        stages.append((name, value, EVALUATION_STAGE_FLAG))

    if not stages:
        LOG.warning("No stages found, nothing to do")
        return 0

    # For quick mapping of name to ID
    stages_name_to_id = {stage[0]: i for i, stage in enumerate(stages)}

    # nodes just numbers from 0 to N_nodes - 1
    # edges are 2-tuples of node IDs, (origin, target)
    edges = []
    for target, stage in enumerate(stages):
        if "deps" not in stage[1]:
            continue
        for dep in stage[1]["deps"]:
            origin = stages_name_to_id[dep]
            edges.append((origin, target))

    # get the object that walks us through the dependencies
    walker = create_graph_walker(len(stages), edges)
    stages_done = get_stages_done()
    if not which_stages:
        which_stages = []
    for name in which_stages:
        # These will always have precedence over "done" status
        walker.set_to_do(stages_name_to_id[name])
    for name in stages_done:
        walker.set_done(stages_name_to_id[name])

    stages_to_do = walker.compute_topology()
    LOG.info("STAGES to do (in this order):")
    for std in stages_to_do:
        LOG.info(f"  -> {stages[std][0]}")
    LOG.info("LET'S GO\n")

    # Now loop stage-by-stage
    for ind in stages_to_do:
        name, value, stage_flag = stages[ind]
        LOG.info(f"--> STAGE {name} <--")
        cwd, cwd_rel = get_stage_work_dir(name, value)
        make_dir(cwd)

        if stage_flag == OPTIMISATION_STAGE_FLAG and not run_optimisation(cwd, name, value):
            LOG.error(f"There was a problem in optimisation stage: {name}")
            return 1
        if stage_flag == USER_STAGE_FLAG and not run_cmd_or_python(cwd, name, value):
            LOG.error(f"There was a problem in custom stage: {name}")
            return 1
        if stage_flag == EVALUATION_STAGE_FLAG and not run_inspector(cwd, value, stages_optimisation):
            LOG.error(f"There was a problem in evaluation stage: {name}")
            return 1
        walker.set_done(ind)
        set_stage_done(name, cwd_rel)

    return 0


def run(args):
    """
    arparse will execute this function
    """
    set_work_dir(abspath(expanduser(args.work_dir)))
    # This will already fail if the config is found not to be sane
    config = load_config(args.config)
    # prepare the working directory
    prepare_work_dir()
    # run all stages
    return run_stages(config, args.stages)


def main():

    parser = argparse.ArgumentParser(description="o2tuner optimisation entry point")
    parser.set_defaults(func=run)
    parser.add_argument("-c", "--config", help="your configuration", required=True)
    parser.add_argument("-d", "--work-dir", dest="work_dir", help="The working directory to run in", required=True)
    parser.add_argument("--stages", nargs="*", help="run until this stage")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
