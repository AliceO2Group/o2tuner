"""
The cut tuning optimisation run
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


def run_cmd_or_python(cwd, name, config):
    if "cmd" not in config and "python" not in config:
        print("ERROR: Need either the cmd or python section in the config")
        return False
    if "python" in config:
        path = config["python"].get("file", None)
        entrypoint = config["python"].get("entrypoint", None)
        if not path or not entrypoint:
            print("ERROR: Need path to python file and entrypoint function")
            return False
        user_config = config.get("config", {})
        # import function to be execuuted
        func = import_function_from_file(path, entrypoint)
        # cache current directory
        this_dir = getcwd()
        # change to this cwd and afterwards back
        chdir(cwd)
        ret = func(user_config)
        chdir(this_dir)
        return ret
    # We need to extract the return code here in a reasonable manner
    # It is not well defined to just get it via psutil.Process.wait() since it can happen
    # that the process is already done and return code can not even be found in the
    # system's process table anymore
    run_command(config["cmd"], cwd=cwd, log_file=config.get("log_file", f"{name}.log"), wait=True)
    return True


def run_optimisation(cwd, config):
    """
    Wrapper to run the optimisation.
    """
    func_name = config.get("entrypoint", config.get("objective", None))
    func = import_function_from_file(config["file"], func_name)
    optuna_config = {k: v for k, v in config.items() if k not in ("entrypoint", "objective", "script")}

    user_config = config.get("config", {})
    # cache current directory
    this_dir = getcwd()
    # change to this cwd and afterwards back
    chdir(cwd)
    ret = optimise(func, optuna_config, work_dir=cwd, user_config=user_config)
    chdir(this_dir)
    return ret


def run_stages(config, which_stages):  # noqa: C901
    """
    Run the stages defined in the config specified by the user
    Run all if nothing is specified
    """
    work_dir = get_work_dir()
    stages_user = config.get("stages_user", {})
    stages_optimisation = config.get("stages_optimisation", {})

    # Flag normal user stages with False to indicate that this is not an optimisation step
    stages = [(name, value, False) for name, value in stages_user.items()]
    for name, value in stages_optimisation.items():
        # Instead, flag these stages with True to indicate these are optimisation steps
        stages.append((name, value, True))

    if not stages:
        print("WARNING: No stages found, nothing to do")
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
    print("STAGES to do (in this order):")
    for std in stages_to_do:
        print(f"  -> {stages[std][0]}")
    print("LET'S GO\n")

    # Now loop stage-by-stage
    for ind in stages_to_do:
        name, value, is_optimisation = stages[ind]
        print(f"--> STAGE {name} <--")
        cwd_rel = value.get("cwd", name)
        cwd = join(work_dir, cwd_rel)
        make_dir(cwd)

        if is_optimisation and not run_optimisation(cwd, value):
            print(f"There was a problem in OPTIMISATION stage {name}")
            return 1
        if not is_optimisation and not run_cmd_or_python(cwd, name, value):
            print(f"There was a problem in CUSTOM  stage {name}")
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
