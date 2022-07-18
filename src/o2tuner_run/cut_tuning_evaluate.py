"""
The cut tuning evaluation run
"""

import sys
import argparse
from os.path import join

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from o2tuner.inspector import OptunaInspector
from o2tuner.io import parse_yaml


def plot_base(x, y, ax=None, title=None, **plot_kwargs):
    """
    wrapper around plotting x and y to an axes
    """
    if not ax:
        ax = plt.gca()
    if len(x) != len(y):
        print(f"WARNING: Not going to plot for different lengths of x ({len(x)}) and y ({len(y)})")
        return ax
    ax.plot(x, y, **plot_kwargs)
    if title:
        ax.set_title(title)
    return ax


def plot_steps_hits_loss(insp, user_config, out_dir):
    """
    Helper function to plot steps and hits
    """

    # get everything we want to plot from the inspector
    steps = insp.get_annotation_per_trial("rel_steps")
    y_axis_all = insp.get_annotation_per_trial("rel_hits")
    losses = insp.get_losses()

    # X ticks just from 1 to n iterations
    x_axis = range(1, len(steps) + 1)

    figure, ax = plt.subplots(figsize=(30, 10))
    linestyles = ["--", ":", "-."]
    colors = list(mcolors.TABLEAU_COLORS.values())
    # first iterate through colors, then through lines styles
    line_style_index = 0

    # plot hits
    # loop through all detectors, indexing corresponds to their place in the user configuration
    for i, det in enumerate(user_config["O2DETECTORS"]):
        if i > 0 and not i % len(colors):
            line_style_index += 1
        y_axis = [yax[i] for yax in y_axis_all]
        if None in y_axis:
            continue
        plot_base(x_axis, y_axis, ax, label=det, linestyle=linestyles[line_style_index], color=colors[i % len(colors)], linewidth=2)

    # add steps to plot
    plot_base(x_axis, steps, ax, linestyle="-", linewidth=2, color="black", label="STEPS")
    # add loss to plot, make new axis to allow different scale
    ax_loss = ax.twinx()
    ax_loss.set_ylabel("LOSS", color="gray", fontsize=20)
    plot_base(x_axis, losses, ax_loss, linestyle="", marker="x", markersize=20, linewidth=2, color="gray")
    ax_loss.tick_params(axis="y", labelcolor="gray", labelsize=20)

    ax.set_xlabel("iteration", fontsize=20)
    ax.set_ylabel("rel. value hits, steps", fontsize=20)
    ax.tick_params(axis="both", labelsize=20)
    ax.legend(loc="best", ncol=4, fontsize=20)

    figure.tight_layout()
    figure.savefig(join(out_dir, "steps_hits_history.png"))
    plt.close(figure)


def run(args):
    insp = OptunaInspector(args.optuna_config)
    insp.load()

    if not args.user_config:
        print("WARNING: Cannot do the step and hits history without the user configuration")
        return 0

    user_config = parse_yaml(args.user_config) if args.user_config else None
    map_params = {}

    if user_config:
        plot_steps_hits_loss(insp, user_config, args.output)
        # at the same time, extract mapping of optuna parameter names to actual meaningful names related to the task at hand
        counter = 0
        for med_id in user_config["index_to_med_id"]:
            for param in user_config["REPLAY_CUT_PARAMETERS"]:
                map_params[str(counter)] = f"{param} of {med_id}"
                counter += 1
    else:
        print("WARNING: Cannot do the step and hits history without the user configuration")

    figure, _ = insp.plot_importance(map_params=map_params, n_most_important=50)
    figure.tight_layout()
    figure.savefig(join(args.output, "importance_parameters.png"))
    plt.close(figure)

    figure, _ = insp.plot_parallel_coordinates(map_params=map_params)
    figure.savefig(join(args.output, "parallel_coordinates.png"))
    plt.close(figure)

    figure, _ = insp.plot_slices(map_params=map_params)
    figure.savefig(join(args.output, "slices.png"))
    plt.close(figure)

    figure, _ = insp.plot_correlations(map_params=map_params)
    figure.savefig(join(args.output, "parameter_correlations.png"))
    plt.close(figure)

    figure, _ = insp.plot_pairwise_scatter(map_params=map_params)
    figure.savefig(join(args.output, "pairwise_scatter.png"))
    plt.close(figure)

    return 0


def main():
    parser = argparse.ArgumentParser(description="GEANT cut optimisation")
    parser.set_defaults(func=run)
    parser.add_argument("-c", "--optuna-config", dest="optuna_config", help="the optuna configuration", required=True)
    parser.add_argument("-u", "--user-config", dest="user_config", help="path to user configuration")
    parser.add_argument("-o", "--output", help="output directory")
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
