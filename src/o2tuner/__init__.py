"""
o2tuner module
"""

import sys
from pkg_resources import require
from o2tuner.argumentparser import O2TunerArgumentParser
from o2tuner.o2tuner import O2Tuner, O2TunerError
from o2tuner.backends import OptunaHandler
from o2tuner.log import Log


def objective(trial):
    x_var = trial.suggest_float("x", -10, 10)
    return (x_var-2)**2


LOG = Log()


def entrypoint():
    arg_parser = O2TunerArgumentParser()
    arg_parser.gen_config_help(O2Tuner.get_default_conf())
    args = arg_parser.parse_args()

    LOG.set_quiet(args.quiet)

    try:
        process_actions(args)
    except O2TunerError as exc:
        LOG.error(f"Cannot continue: {exc}")
        sys.exit(10)


def process_actions(args):
    if args.version:
        ver = str(require(__package__)[0].version)
        if ver == "LAST-TAG":
            ver = "development version"
        print(f"{__package__} {ver}")
        return

    optuna_handler = OptunaHandler()
    optuna_handler.set_objective(objective)

    # Create and run the tuner
    tuner = O2Tuner(optuna_handler)

    if args.action in ["run"]:
        process_run(tuner, args)
    else:
        assert False, "invalid action"


def process_run(o2_tuner, args):
    if args.action == "run":
        LOG.info("Running ...")
        o2_tuner.init(n_trials=50)
        o2_tuner.run()
