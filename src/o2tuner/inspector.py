"""
Mainstream and custom backends should be placed here
"""
import sys
from math import sqrt, ceil
from collections import OrderedDict

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mplc
import matplotlib.cm as mplcm
import matplotlib.colorbar as mplcb
from matplotlib.lines import Line2D
import seaborn as sns
import pandas as pd

from optuna.importance import get_param_importances
from optuna.study._study_direction import StudyDirection
from optuna.trial import TrialState

from o2tuner.io import parse_yaml, dump_yaml
from o2tuner.backends import load_or_create_study
from o2tuner.sampler import construct_sampler
from o2tuner.log import Log

LOG = Log()


class O2TunerInspector:
    """
    Inspect optuna study
    """

    def __init__(self):
        """
        Constructor
        """
        # the full study to be investigated
        self._study = None
        # cache importances of parameters
        self._importances = None
        # cache eompleted trials
        self._trials_complete = None
        # map internal parameter names to something else (optional)
        self._parameter_map = None

    def load(self, opt_config=None, opt_work_dir=None):
        """
        Loading wrapper
        """
        if not opt_config and not opt_work_dir:
            LOG.warning("Nothing to load, no configuration given")
            return False
        if isinstance(opt_config, str):
            opt_config = parse_yaml(opt_config)
        if not opt_config:
            opt_config = {}
        sampler = construct_sampler(opt_config.get("sampler", None))
        storage = opt_config.get("study", {})
        _, self._study = load_or_create_study(storage.get("name", None), storage.get("storage", None), sampler, opt_work_dir,
                                              create_if_not_exists=False)
        # Use only successfully completed trials
        trials_state = self._study.trials_dataframe(("state",))["state"].values
        self._trials_complete = [trial for trial, state in zip(self._study.trials, trials_state) if state == TrialState.COMPLETE.name]
        # now we sort the trials according to the order in which they were done
        trial_numbers = [trial.number for trial in self._trials_complete]
        self._trials_complete = [t for _, t in sorted(zip(trial_numbers, self._trials_complete))]

        return True

    def write_summary(self, filepath="o2tuner_optimisation_summary.yaml"):
        """
        Write a short summary to YAML file
        """
        LOG.info(f"Writing optimisation summary to {filepath}")
        best_trial = self._study.best_trial
        user_attrs = best_trial.user_attrs
        to_write = {"n_trials": len(self._study.trials),
                    "best_trial_cwd": user_attrs.get("cwd", "./"),
                    "best_trial_number": best_trial.number,
                    "best_trial_loss": self._study.best_value,
                    "best_trial_parameters": self._study.best_params}
        dump_yaml(to_write, filepath)

    def get_annotation_per_trial(self, key, accept_missing_annotation=True):
        """
        Assemble history of requested annotation
        """
        if accept_missing_annotation:
            return [t.user_attrs[key] if key in t.user_attrs else None for t in self._trials_complete]
        ret_list = []
        for trial in self._trials_complete:
            user_attrs = trial.user_attrs
            if key not in user_attrs:
                LOG.error(f"Key {key} not in trial number {trial.number}.")
                sys.exit(1)
            ret_list.append(user_attrs[key])
        return ret_list

    def get_losses(self):
        """
        Simply return list of losses
        """
        return [t.value for t in self._trials_complete]

    def set_parameter_name_map(self, param_map):
        """
        Map parameter names to probably something more meaningful defined by the user
        """
        self._parameter_map = param_map

    def map_parameter_names(self, parameter_names_raw):
        """
        Map parameter names to probably something more meaningful defined by the user
        """
        if not self._parameter_map:
            return parameter_names_raw
        return [self._parameter_map[pn] if pn in self._parameter_map else pn for pn in parameter_names_raw]

    def get_params_importances(self, n_most_important=None):
        """
        Get most important parameters
        """
        if not self._importances:
            importances = get_param_importances(self._study, evaluator=None, params=None, target=None)
            self._importances = OrderedDict(reversed(list(importances.items())))

        if not n_most_important:
            n_most_important = len(self._importances)

        # get importances of parameters
        importance_values = list(self._importances.values())
        n_most_important = min(n_most_important, len(self._importances))
        importance_values = importance_values[-n_most_important:]

        # get parameter names
        param_names = list(self._importances.keys())
        param_names = param_names[-n_most_important:]

        return param_names[:n_most_important], importance_values[:n_most_important]

    def plot_importance(self, *, n_most_important=None):
        """
        Plot the importance of parameters
        Most of it based on https://optuna.readthedocs.io/en/stable/_modules/optuna/visualization/_param_importances.html#plot_param_importances

        However, add some functionality we would like to have here
        """
        LOG.info("Plotting importance")
        param_names, importance_values = self.get_params_importances(n_most_important)
        param_names = self.map_parameter_names(param_names)

        figure, ax = plt.subplots(figsize=(30, 10))
        y_pos = [i for i, _ in enumerate(importance_values)]
        ax.barh(y_pos, importance_values)
        ax.set_yticks(y_pos, labels=param_names)
        ax.set_xlabel("parameter importance", fontsize=30)
        ax.set_ylabel("parameter", fontsize=30)
        ax.tick_params("both", labelsize=20)

        return figure, ax

    def plot_parallel_coordinates(self, *, n_most_important=None):
        """
        Plot parallel coordinates. Each horizontal line represents a trial, each vertical line a parameter
        """
        LOG.info("Plotting parallel coordinates")
        params, _ = self.get_params_importances(n_most_important)

        losses = self.get_losses()
        curves = [[] for _ in losses]
        skip_trials = {}

        for i, trial in enumerate(self._trials_complete):
            for param_key in params:
                if param_key not in trial.params:
                    skip_trials[i] = True
                    continue
                curves[i].append(trial.params[param_key])

        # re-map parameter names
        params = self.map_parameter_names(params)

        # order trials by loss and prepare colorbar
        norm_colors = mplc.Normalize(vmin=min(losses), vmax=max(losses))
        # colorbar and sorting of losses reversed if needed
        cmap, reverse = (mplcm.get_cmap("Blues_r"), True) if self._study.direction == StudyDirection.MINIMIZE else (mplcm.get_cmap("Blues"), False)
        curves = [c for _, c in sorted(zip(losses, curves), reverse=reverse)]
        # make sure curves of best losses are plotted last and hence on top
        losses.sort(reverse=reverse)
        x_axis = list(range(len(params) + 1))
        figure, axes = plt.subplots(1, len(params) + 1, figsize=(30, 10))
        for i, (loss, curve) in enumerate(zip(losses, curves)):
            if i in skip_trials:
                continue
            for ax in axes[:-1]:
                ax.plot(x_axis[:-1], curve, c=cmap(norm_colors(loss)))
        for i, ax in enumerate(axes[:-1]):
            ax.set_xticks(x_axis[:-1], labels=params, rotation=45, fontsize=20)
            ax.set_xlim(x_axis[i], x_axis[i+1])
            ylims = ax.get_ylim()
            ylims_diff = ylims[1] - ylims[1]
            y_low, y_up = (ylims[0] - 0.1 * ylims_diff, ylims[1] + 0.1 * ylims_diff)
            ax.set_ylim(y_low, y_up)
            ax.get_yaxis().set_ticks([y_low, y_up])
            ax.tick_params("y", labelsize=20)
            # trick to hide horizontal axis
            ax.spines['bottom'].set_alpha(0)
            ax.spines['top'].set_alpha(0)

        cbar = mplcb.ColorbarBase(axes[-1], cmap="Blues_r", norm=norm_colors, ticks=[min(losses), max(losses)])
        cbar.ax.tick_params(labelsize=20)
        cbar.ax.set_ylabel("loss", fontsize=20)
        figure.subplots_adjust(wspace=0)
        figure.suptitle("Parallel coordinates", fontsize=40)

        return figure, axes

    def plot_slices(self, *, n_most_important=None):
        """
        Plot slices
        """
        LOG.info("Plotting slices")
        params, _ = self.get_params_importances(n_most_important)

        n_rows = ceil(sqrt(len(params)))
        n_cols = n_rows
        if len(params) > n_rows**2:
            n_rows += 1

        losses = self.get_losses()
        figure, axes = plt.subplots(n_rows, n_cols, figsize=(50, 50))
        axes = axes.flatten()

        norm_colors = mplc.Normalize(vmin=0, vmax=len(losses) - 1)
        cmap = mplcm.get_cmap("Blues")

        # re-map parameter names
        params_labels = self.map_parameter_names(params)

        for param_key, label, ax in zip(params[::-1], params_labels[::-1], axes):
            values = []
            this_losses = []
            for trial, loss in zip(self._trials_complete, losses):
                if param_key not in trial.params:
                    continue
                values.append(trial.params[param_key])
                this_losses.append(loss)
            ax.scatter(values, this_losses, cmap=cmap, norm=norm_colors, c=range(len(this_losses)))
            ax.set_xlabel(f"value of parameter {label}", fontsize=30)
            ax.set_ylabel("loss", fontsize=30)
            ax.tick_params(labelsize=30)

        for ax in axes[len(params):]:
            ax.set_visible(False)

        figure.suptitle("Loss as function of param values", fontsize=40)

        return figure, axes

    def plot_correlations(self, *, n_most_important=None):
        """
        Plot correlation among parameters
        """
        LOG.info("Plotting parameter correlations")
        params, _ = self.get_params_importances(n_most_important)
        params_labels = self.map_parameter_names(params)

        param_values = []
        params_plot = []
        for param_key, label in zip(params[::-1], params_labels[::-1]):
            values = [trial.params.get(param_key, np.NAN) for trial in self._trials_complete]
            param_values.append(values)
            params_plot.append(label)

        df = pd.DataFrame(list(zip(*param_values)), columns=params_plot)
        corr = df.corr()
        # Generate a mask for the upper triangle
        mask = np.triu(np.ones_like(corr, dtype=bool))

        # Set up the matplotlib figure
        figure, ax = plt.subplots(figsize=(20, 20))

        # Generate a custom diverging colormap
        cmap = sns.diverging_palette(230, 20, as_cmap=True)

        # Draw the heatmap with the mask and correct aspect ratio
        sns.heatmap(corr, mask=mask, cmap=cmap, vmax=1, vmin=-1, center=0, square=True, linewidths=.5, cbar_kws={"shrink": .5})
        ax.tick_params(axis="x", rotation=90)
        ax.tick_params(axis="both", labelsize=20)
        # set label size of colorbar to 20
        ax.collections[0].colorbar.ax.tick_params(labelsize=20)

        return figure, ax

    def plot_pairwise_scatter(self, *, n_most_important=None):
        """
        Plot correlation among parameters
        """
        LOG.info("Plotting pair-wise scatter")
        params, _ = self.get_params_importances(n_most_important)
        params_labels = self.map_parameter_names(params)

        param_values = []
        params_plot = []
        for param_key, label in zip(params[::-1], params_labels[::-1]):
            values = [trial.params.get(param_key, np.NAN) for trial in self._trials_complete]
            param_values.append(values)
            params_plot.append(label)

        df = pd.DataFrame(list(zip(*param_values)), columns=params_plot)

        # Draw the heatmap with the mask and correct aspect ratio
        pair_grid = sns.pairplot(df, height=1.8, aspect=1.8, plot_kws={"edgecolor": "k", "linewidth": 0.5}, diag_kind="kde", diag_kws={"fill": True},
                                 corner=False)

        return pair_grid.figure, pair_grid

    def plot_loss_feature_history(self, *, n_most_important=None):
        """
        Plot parameter and loss history and add correlation of each parameter and loss
        """
        LOG.info("Plot loss and feature history")
        params, _ = self.get_params_importances(n_most_important)
        params_labels = self.map_parameter_names(params)

        # find the trials where the loss got better for the first time
        losses = self.get_losses()
        better_iterations = [0]
        current_best = losses[0]
        for i, loss in enumerate(losses[1:], start=1):
            if loss < current_best:
                current_best = loss
                better_iterations.append(i)

        param_values = []
        params_plot = []
        for param_key, label in zip(params[::-1], params_labels[::-1]):
            values = [trial.params.get(param_key, np.NAN) for trial in self._trials_complete]
            param_values.append(values)
            params_plot.append(label)

        # include the loss in the last row
        param_values.append(losses)
        params_plot.append("loss")
        params_labels.append("loss")
        df = pd.DataFrame(list(zip(*param_values)), columns=params_plot)

        # compute correlations and get "loss" column which has the data interesting for us
        corr_loss = df.corr()["loss"].values
        x_axis = range(len(param_values[0]))

        # Set up the matplotlib figure
        figure, axes = plt.subplots(len(params_labels) + 1, 1, sharex=True, figsize=(20, 40))
        axes = axes.flatten()
        for i, (ax, name, values, corr) in enumerate(zip(axes, params_labels, param_values, corr_loss)):
            title = f"{name}, correlation with loss: {corr}"
            color = "tab:blue"
            if i == len(axes) - 2:
                title = "loss"
                color = "black"

            ax.plot(x_axis, values, linewidth=2, color=color)
            ax.plot(better_iterations, [values[i] for i in better_iterations], color="tab:orange", linestyle="--", linewidth=2)
            ax.set_xlabel("iteration", fontsize=20)
            min_value = min(values)
            if min_value > 0 and max(values) / min_value > 10:
                ax.set_yscale("log")
            ax.set_ylabel("value", fontsize=20)
            ax.tick_params("both", labelsize=20)
            ax.set_title(title, fontsize=20)

        legend_lines = [Line2D([0], [0], color="black", lw=2),
                        Line2D([0], [0], color="black", lw=2, ls="--")]

        axes[-1].legend(legend_lines, ["value", "value at next best loss"], loc="center", ncol=2, mode="expand", fontsize=20)
        axes[-1].axis("off")

        return figure, axes
