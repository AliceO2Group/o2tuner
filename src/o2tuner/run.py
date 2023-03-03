"""
Utility to run stages, bound to main entrypoint run action
"""
from os.path import join, abspath, expanduser, dirname
from os import getcwd, chdir

from o2tuner.system import run_command, import_function_from_file
from o2tuner.optimise import optimise
from o2tuner.io import make_dir
from o2tuner.config import Configuration, get_work_dir, CONFIG_STAGES_USER_KEY, CONFIG_STAGES_OPTIMISATION_KEY, CONFIG_STAGES_EVALUATION_KEY
from o2tuner.graph import create_graph_walker
from o2tuner.inspector import O2TunerInspector
from o2tuner.log import Log

LOG = Log()


def get_stage_work_dir(name, config):
    """
    Get the working directory name of a given stage by its name
    """
    cwd_rel = config.get("cwd", name)
    return join(get_work_dir(), cwd_rel), cwd_rel


def run_cmd_or_python(cwd, name, config):
    """
    Run a user python function from a given file or simply a command line
    """
    if "python" in config:
        # import function to be executed
        func = import_function_from_file(config["python"]["file"], config["python"]["entrypoint"])
        # cache current directory
        this_dir = getcwd()
        # change to this cwd and afterwards back
        chdir(cwd)
        if user_config := config["config"]:
            ret = func(user_config)
        else:
            ret = func()
        chdir(this_dir)
        return ret
    run_command(config["cmd"], cwd=cwd, log_file=config.get("log_file", f"{name}.log"), wait=True)
    return True


def run_optimisation(cwd, config):
    """
    Wrapper to run the optimisation.
    """
    func_name = config["entrypoint"]
    func = import_function_from_file(config["file"], func_name)
    if not func:
        return False
    # cache current directory
    this_dir = getcwd()
    # change to this cwd and afterwards back
    chdir(cwd)
    ret = optimise(func, config["optuna_config"], work_dir="./", user_config=config["config"])
    chdir(this_dir)
    return ret


def run_inspector(cwd, config, stages_optimisation):
    """
    Wrapper to run the optimisation.
    """
    func_name = config["entrypoint"]
    func = import_function_from_file(config["file"], func_name)
    if not func:
        return False

    inspectors = []

    for optimisation in config["optimisations"]:
        if optimisation not in stages_optimisation:
            LOG.warning(f"Optimisation stage {optimisation} not defined, cannot construct inspector for that. Skip...")
            continue
        opt_config = stages_optimisation[optimisation]
        opt_cwd, _ = get_stage_work_dir(optimisation, opt_config)
        insp = O2TunerInspector()
        if not insp.load(opt_config["optuna_config"], opt_cwd):
            continue
        inspectors.append(insp)

    if not inspectors:
        LOG.warning("No O2TunerInspectors loaded, nothing to do")
        return False

    # cache current directory
    this_dir = getcwd()
    # change to this cwd and afterwards back
    chdir(cwd)
    ret = func(inspectors, config["config"])
    chdir(this_dir)
    return ret


def run_stages(config, which_stages):  # noqa: C901
    """
    Run the stages defined in the config specified by the user
    Run all if nothing is specified
    """

    stages = config.all_stages
    stages_optimisation = config.get_stages_optimisation()

    if not stages:
        LOG.warning("No stages found, nothing to do")
        return 0

    # For quick mapping of name to ID
    stages_name_to_id = {stage[0]: i for i, stage in enumerate(stages)}

    # nodes just numbers from 0 to N_nodes - 1
    # edges are 2-tuples of node IDs, (origin, target)
    edges = []
    for target, stage in enumerate(stages):
        for dep in stage[1].get("deps", []):
            origin = stages_name_to_id[dep]
            edges.append((origin, target))

    # get the object that walks us through the dependencies
    walker = create_graph_walker(len(stages), edges)
    stages_done = config.get_stages_done()
    if not which_stages:
        which_stages = []
    for name in which_stages:
        # These will always have precedence over "done" status
        if name not in stages_name_to_id:
            LOG.error(f"Requested stage {name} is unknown")
            return 1
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

        if stage_flag == CONFIG_STAGES_OPTIMISATION_KEY and not run_optimisation(cwd, value):
            LOG.error(f"There was a problem in optimisation stage: {name}")
            return 1
        if stage_flag == CONFIG_STAGES_USER_KEY and not run_cmd_or_python(cwd, name, value):
            LOG.error(f"There was a problem in custom stage: {name}")
            return 1
        if stage_flag == CONFIG_STAGES_EVALUATION_KEY and not run_inspector(cwd, value, stages_optimisation):
            LOG.error(f"There was a problem in evaluation stage: {name}")
            return 1
        walker.set_done(ind)
        config.set_stage_done(name, cwd_rel)

    return 0


def run(args):
    """
    arparse will execute this function
    """
    # This will already fail if the config is found not to be sane
    config = Configuration(args.config, args.script_dir or dirname(args.config))
    config.set_work_dir(abspath(expanduser(args.work_dir)))
    # prepare the working directory
    config.prepare_work_dir()
    # run all stages
    return run_stages(config, args.stages)
