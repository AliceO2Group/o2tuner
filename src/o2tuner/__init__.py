"""
o2tuner main module
"""

import sys
from pkg_resources import require
from o2tuner.argumentparser import O2TunerArgumentParser
from o2tuner.exception import O2TunerFatal
from o2tuner.log import get_logger, configure_logger

from o2tuner.run import run


LOG = get_logger()


def entrypoint():
    """
    Global entrypoint to O2Tuner
    """
    arg_parser = O2TunerArgumentParser()
    # arg_parser.gen_config_help(O2Tuner.get_default_conf())
    args = arg_parser.parse_args()
    configure_logger(args.debug, args.verbosity)

    try:
        process_actions(args)
    except O2TunerFatal as exc:
        LOG.error("Cannot continue: %s", exc)
        sys.exit(10)


def process_actions(args):
    """
    Steer the chosen action to be executed
    """
    if args.version:
        ver = str(require(__package__)[0].version)
        if ver == "LAST-TAG":
            ver = "development version"
        print(f"{__package__} {ver}")
        return

    if args.action in ["run"]:
        process_run(args)
    else:
        assert False, "invalid action"


def process_run(args):
    """
    Forward arguments to the central run function
    """
    if args.action == "run":
        run(args)
