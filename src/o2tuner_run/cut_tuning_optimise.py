"""
The cut tuning optimisation run
"""

import sys
import argparse
from os.path import join, abspath
from os import environ

import numpy as np

from o2tuner.system import run_command
from o2tuner.utils import make_trial_directory, annotate_trial
from o2tuner.optimise import optimise
from o2tuner.io import parse_json, dump_json, exists_file, remove_dir

# Get environment variables we need to execute some cmds
O2_ROOT = environ.get("O2_ROOT")
MCSTEPLOGGER_ROOT = environ.get("MCSTEPLOGGER_ROOT")


def extract_hits(path, o2_detectors, det_name_to_id):
    """
    Retrieve the number of hits per detector
    """
    hits = [None] * len(o2_detectors)
    with open(path, "r", encoding="utf8") as hit_file:
        for line in hit_file:
            fields = line.split()
            if not fields:
                continue
            if fields[0] in o2_detectors:
                pot_nan = fields[1].lower()
                if "nan" in pot_nan:
                    hits[det_name_to_id[fields[0]]] = None
                    continue
                # NOTE relying on the first field containing the number of hits, this may change if the O2 macro changes
                hits[det_name_to_id[fields[0]]] = float(fields[1])
        return hits


def extract_avg_steps(path):
    """
    Retrieve the average number of original and skipped steps
    """
    search_string = "Original number, skipped, kept, skipped fraction and kept fraction of steps"
    extract_start = len(search_string.split())
    steps_orig = []
    steps_skipped = []
    with open(path, "r", encoding="utf8") as step_file:
        for line in step_file:
            if search_string in line:
                line = line.split()
                steps_orig.append(int(line[extract_start]))
                steps_skipped.append(int(line[extract_start + 1]))
    if not steps_orig:
        print("ERROR: Could not extract steps")
        sys.exit(1)
    return sum(steps_orig) / len(steps_orig), sum(steps_skipped) / len(steps_skipped)


def loss_and_metrics(hits_path, hits_ref_path, step_path, o2_detectors, rel_hits_cutoff):
    """
    Compute the loss and return steps and hits relative to the baseline
    """
    hits_opt = extract_hits(hits_path, o2_detectors, {n: i for i, n in enumerate(o2_detectors)})
    hits_ref = extract_hits(hits_ref_path, o2_detectors, {n: i for i, n in enumerate(o2_detectors)})
    rel_hits = [h / r if (h is not None and r is not None and r > 0) else None for h, r in zip(hits_opt, hits_ref)]
    rel_hits_valid = [rh for rh in rel_hits if rh is not None]

    steps = extract_avg_steps(step_path)
    rel_steps = 1 - (steps[1] / steps[0])

    loss = rel_steps**2
    for rvh in rel_hits_valid:
        penalty = 2 if rvh < rel_hits_cutoff else 1
        loss += penalty * (rel_hits_cutoff - rvh)**2

    loss = loss / (len(rel_hits_valid) + 1)
    return loss, rel_steps, rel_hits


def mask_params(params, index_to_med_id, replay_cut_parameters):
    """
    Provide a mask and only enable indices for provided parameters
    (or all, if none are given)
    """
    if not params:
        return np.tile(np.full(len(replay_cut_parameters), True), len(index_to_med_id))
    mask = np.full(len(replay_cut_parameters), False)
    replay_param_to_id = {v: i for i, v in enumerate(replay_cut_parameters)}
    for par in params:
        mask[replay_param_to_id[par]] = True
    return np.tile(mask, len(index_to_med_id))


def unmask_modules(modules, replay_cut_parameters, index_to_med_id, passive_medium_ids_map, detector_medium_ids_map):
    """
    Un-mask all indices for a given list of modules
    """
    mask = np.full(len(index_to_med_id) * len(replay_cut_parameters), False)
    mod_med_map = {**passive_medium_ids_map, **detector_medium_ids_map}
    med_id_to_index = {med_id: i for i, med_id in enumerate(index_to_med_id)}

    for mod, medium_ids in mod_med_map.items():
        if mod not in modules:
            continue
        for mid in medium_ids:
            index = med_id_to_index[mid]
            mask[index * len(replay_cut_parameters):(index + 1) * len(replay_cut_parameters)] = True
    return mask


def arrange_to_space(arr, n_params, index_to_med_id):
    return {med_id: list(arr[i * n_params:((i + 1) * n_params)]) for i, med_id in enumerate(index_to_med_id)}


def make_o2_format(space_drawn, ref_params_json, passive_medium_ids_map, replay_cut_parameters):
    """
    Write the parameters and values in a JSON structure readible by O2MaterialManager
    """
    params = parse_json(ref_params_json)
    for module, batches in params.items():
        if module in ["default", "enableSpecialCuts", "enableSpecialProcesses"]:
            continue
        for batch in batches:
            med_id = batch["global_id"]
            # according to which modules are recognised by this script
            if module in passive_medium_ids_map:
                batch["cuts"] = dict(zip(replay_cut_parameters, space_drawn[med_id]))
    return params


def objective_cut_tuning(trial, user_config):
    """
    The central objective funtion for the optimisation
    """

    # make params we want to have
    mask = mask_params(user_config["params"], user_config["index_to_med_id"], user_config["REPLAY_CUT_PARAMETERS"])
    mask_passive = unmask_modules(user_config["modules"],
                                  user_config["REPLAY_CUT_PARAMETERS"],
                                  user_config["index_to_med_id"],
                                  user_config["passive_medium_ids_map"],
                                  user_config["detector_medium_ids_map"])
    mask = mask & mask_passive

    # get next estimation for parameters
    this_array = np.full((len(mask,)), -1.)
    for i, param in enumerate(mask):
        if not param:
            continue
        this_array[i] = trial.suggest_loguniform(f"{i}", user_config["search_value_low"], user_config["search_value_up"])
    space_drawn = arrange_to_space(this_array, len(user_config["REPLAY_CUT_PARAMETERS"]), user_config["index_to_med_id"])

    # make our working directory for this trial
    cwd = make_trial_directory(trial)

    # dump the JSONs. The first is digested by the MCReplay engine...
    param_file_path = join(cwd, "cuts.json")
    dump_json(space_drawn, param_file_path)

    # ...and the second can be used to directly to O2 --confKeyValues
    space_drawn_o2 = make_o2_format(space_drawn, user_config["reference_params_o2"], user_config["passive_medium_ids_map"],
                                    user_config["REPLAY_CUT_PARAMETERS"])
    param_file_path_o2 = join(cwd, "cuts_o2.json")
    dump_json(space_drawn_o2, param_file_path_o2)

    # replay the simulation
    cut_file_param = ";MCReplayParam.cutFile=cuts.json"
    cmd = f'o2-sim-serial -n {user_config["n_events"]} -g extkinO2 --extKinFile {user_config["kine_file"]} -e MCReplay --skipModules ZDC ' \
          f'--configKeyValues="MCReplayParam.stepFilename={user_config["step_file"]}{cut_file_param}"'
    _, sim_file = run_command(cmd, cwd, log_file="sim.log", wait=True)

    # extract the hits using O2 macro and pipe to file
    extract_hits_root = abspath(join(O2_ROOT, "share", "macro", "analyzeHits.C"))
    cmd_extract_hits = f"root -l -b -q {extract_hits_root}"
    _, hit_file = run_command(cmd_extract_hits, cwd, log_file="hits.dat", wait=True)

    # compute the loss and further metrics...
    baseline_dir = user_config["baseline_dir"]
    baseline_hits_file = join(baseline_dir, "hits.dat")
    loss, rel_steps, rel_hits = loss_and_metrics(hit_file, baseline_hits_file, sim_file, user_config["O2DETECTORS"], user_config["rel_hits_cutoff"])

    # ...and annotate drawn space and metrics to trial so we can re-use it
    annotate_trial(trial, "space", list(this_array))
    annotate_trial(trial, "rel_steps", rel_steps)
    annotate_trial(trial, "rel_hits", rel_hits)

    # remove all the artifacts we don't need to keep space
    remove_dir(cwd, keep=["hits.dat", "cuts.json", "cuts_o2.json", "sim.log"])
    return loss


def init_cut_tuning(user_config):
    """
    An initialisation step done before the actual optimisation

    This is done to create the hits file of the reference in case it has not yet been created
    """
    baseline_dir = user_config["baseline_dir"]
    baseline_hits_file = join(baseline_dir, "hits.dat")
    if not exists_file(baseline_hits_file):
        extract_hits_root = abspath(join(O2_ROOT, "share", "macro", "analyzeHits.C"))
        cmd_extract_hits = f"root -l -b -q {extract_hits_root}"
        run_command(cmd_extract_hits, baseline_dir, log_file="hits.dat", wait=True)
    return 0


def run(args):
    """
    arparse will execute this function
    """
    optimise(objective_cut_tuning, args.optuna_config, user_config=args.user_config, init_func=init_cut_tuning)


def main():

    parser = argparse.ArgumentParser(description="GEANT cut optimisation")
    parser.set_defaults(func=run)
    parser.add_argument("-c", "--optuna-config", dest="optuna_config", help="the optuna configuration", required=True)
    parser.add_argument("-u", "--user-config", dest="user_config", help="path to user configuration")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
