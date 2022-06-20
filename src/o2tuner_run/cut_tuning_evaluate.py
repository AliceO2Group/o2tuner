"""
The cut tuning evaluation run (tbc)
"""

import sys
import argparse

from o2tuner.inspector import OptunaInspector


def run(args):
    insp = OptunaInspector(args.config)
    insp.load()
    insp.visualise(args.output)
    return 0


def main():

    parser = argparse.ArgumentParser(description="GEANT cut optimisation")
    parser.set_defaults(func=run)
    parser.add_argument("config", help="optuna configuration")
    parser.add_argument("-o", "--output", help="output directory")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
