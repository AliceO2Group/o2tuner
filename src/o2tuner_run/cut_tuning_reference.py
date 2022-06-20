"""
The cut tuning reference/basline run
"""

import sys
from os.path import join, abspath
from os import environ
import argparse

from o2tuner.system import run_command
from o2tuner.io import parse_json, make_dir, dump_yaml

O2DETECTORS = ["ITS", "ALPIDE", "TOF", "EMC", "TRD", "PHS", "FT0", "HMP", "MFT", "FDD", "FV0", "MCH", "MID", "CPV", "ZDC", "TPC"]
O2PASSIVE = ["HALL", "PIPE", "CAVE", "MAG", "DIPO", "ABSO", "SHIL", "FRAME", "COMP"]
REPLAY_CUT_PARAMETERS = ["CUTGAM", "CUTELE", "CUTNEU", "CUTHAD", "CUTMUO",
                         "BCUTE", "BCUTM", "DCUTE", "DCUTM", "PPCUTM", "TOFMAX", "CUTALL"]

O2_ROOT = environ.get("O2_ROOT")
O2DPG_ROOT = environ.get("O2DPG_ROOT")
MCSTEPLOGGER_ROOT = environ.get("MCSTEPLOGGER_ROOT")


def digest_parameters(path):
    """
    Extracts the meium ID - module mapping (seperately for detectors and passive modules).
    In addition, we get a mapping from an index to a medium ID.
    Finally, the reference parameters are extracted as a list accorsing to the index mapping.
    """
    reference_params = []
    params = parse_json(path)

    index_to_med_id = []
    passive_medium_ids_map = {}
    # pylint: disable=duplicate-code
    detector_medium_ids_map = {}
    for module, batches in params.items():
        if module in ["default", "enableSpecialCuts", "enableSpecialProcesses"]:
            continue

        for batch in batches:
            med_id = batch["global_id"]
            # according to which modules are recognised by this script
            if module in O2PASSIVE:
                if module not in passive_medium_ids_map:
                    passive_medium_ids_map[module] = []
                passive_medium_ids_map[module].append(med_id)
            elif module in O2DETECTORS:
                if module not in detector_medium_ids_map:
                    detector_medium_ids_map[module] = []
                detector_medium_ids_map[module].append(med_id)
            else:
                continue

            cuts_read = batch.get("cuts", {})
            cuts_append = [cuts_read.get(rcp, -1.) for rcp in REPLAY_CUT_PARAMETERS]

            index_to_med_id.append(med_id)
            reference_params.extend(cuts_append)

    return reference_params, index_to_med_id, passive_medium_ids_map, detector_medium_ids_map


def run(args):
    """
    Called after arguments have been parsed
    """

    # define user configuration which will be also used during optimisation to find paths and some properties
    config = {"n_events": args.nevents,
              "generator": args.generator,
              "engine": args.engine,
              "O2DETECTORS": O2DETECTORS,
              "O2PASSIVE": O2PASSIVE,
              "REPLAY_CUT_PARAMETERS": REPLAY_CUT_PARAMETERS,
              "params": REPLAY_CUT_PARAMETERS[:-1],
              "modules": O2PASSIVE,
              "passive_medium_ids_map": None,
              "detector_medium_ids_map": None,
              "index_to_med_id": None,
              "step_file": None,
              "kine_file": None,
              "baseline_dir": None,
              "reference_params_o2": None,
              "rel_hits_cutoff": 0.95,
              "search_value_low": 0.00001,
              "search_value_up": 1.,
              "reference_values": None}

    #####################
    # The reference run #
    #####################
    ref_dir = join(args.dir, "reference")
    make_dir(ref_dir)
    ref_params = "medium_params_out.json"

    cmd = f'MCSTEPLOG_TTREE=1 LD_PRELOAD={MCSTEPLOGGER_ROOT}/lib/libMCStepLoggerInterceptSteps.so ' \
          f'o2-sim-serial -n {config["n_events"]} -g {config["generator"]} -e {config["engine"]} ' \
          f'--skipModules ZDC --configKeyValues "MaterialManagerParam.outputFile={ref_params}"'
    run_command(cmd, ref_dir, log_file="sim.log", wait=True)

    config["step_file"] = abspath(join(ref_dir, "MCStepLoggerOutput.root"))
    config["kine_file"] = abspath(join(ref_dir, "o2sim_Kine.root"))
    config["reference_params_o2"] = abspath(join(ref_dir, ref_params))
    config["reference_values"], config["index_to_med_id"], config["passive_medium_ids_map"], config["detector_medium_ids_map"] =\
        digest_parameters(join(ref_dir, ref_params))

    ####################
    # The baseline run #
    ####################
    # hen using MCReplay, no RNG is used during stepping. However, during hit creation, RNGs ARE used.
    # During a reference run with GEANT, the same RNGs used during hit creation might might interfer with the stepping.
    # Therefore, to have a well defined number of hits per detector to compare to,
    # we run MCReplay once without any changes of the parameters
    baseline_dir = join(args.dir, "baseline")
    config["baseline_dir"] = abspath(baseline_dir)
    make_dir(baseline_dir)

    cmd = f'o2-sim-serial -n {config["n_events"]} -g extkinO2 --extKinFile {config["kine_file"]} -e MCReplay --skipModules ZDC ' \
          f'--configKeyValues="MCReplayParam.stepFilename={config["step_file"]}"'
    run_command(cmd, baseline_dir, log_file="sim.log", wait=True)

    # write the configuration and we are done, avoid references so we can for instance directly modify modules independent of O2PASSIVE
    dump_yaml(config, join(args.dir, "cut_tuning_config.yaml"), no_refs=True)

    # Let this script produce a configuration for optuna
    dump_yaml({"trials": 10,
               "jobs": 1,
               "workdir": args.dir,
               "study": {"name": None, "storage": None},
               "sampler": {"name": "genetic", "args": {"population_size": 10}}}, join(args.dir, "optuna_config.yaml"))
    return 0


def main():
    """
    Basically the entrypoint
    """
    parser = argparse.ArgumentParser(description="GEANT cut optimisation")
    parser.set_defaults(func=run)
    parser.add_argument("--nevents", "-n", type=int, default=5, help="number of events")
    parser.add_argument("--generator", "-g", help="generator used in reference run", default="pythia8pp")
    parser.add_argument("--engine", "-e", help="engine used in reference run", default="TGeant4")
    parser.add_argument("--dir", "-d", help="top directory where to run", default="cut_tuning")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
