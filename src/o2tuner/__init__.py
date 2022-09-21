"""
o2tuner main module
"""

import sys
from pkg_resources import require
from o2tuner.argumentparser import O2TunerArgumentParser
from o2tuner.tuner import O2TunerError
from o2tuner.log import Log
from o2tuner.run import run


LOG = Log()


def entrypoint():
    arg_parser = O2TunerArgumentParser()
    # arg_parser.gen_config_help(O2Tuner.get_default_conf())
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

    if args.action in ["run"]:
        process_run(args)
    else:
        assert False, "invalid action"


def process_run(args):
    if args.action == "run":
        run(args)
