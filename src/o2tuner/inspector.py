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
import seaborn as sns
import pandas as pd

from optuna.importance import get_param_importances
from optuna.study._study_direction import StudyDirection

from o2tuner.io import parse_yaml
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
        self._study = None
        self._importances = None
        self._opt_user_config = None

    def load(self, opt_config=None, opt_work_dir=None, opt_user_config=None):
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
        _, self._study = load_or_create_study(storage.get("name", None), storage.get("storage", None), sampler, opt_work_dir)
        self._opt_user_config = opt_user_config
        importances = get_param_importances(self._study, evaluator=None, params=None, target=None)
        self._importances = OrderedDict(reversed(list(importances.items())))
        return True

    def get_annotation_per_trial(self, key, accept_missing_annotation=True):
        """
        Assemble history of requested annotation
        """
        if accept_missing_annotation:
            return [t.user_attrs[key] if key in t.user_attrs else None for t in self._study.trials]
        ret_list = []
        for trial in self._study.trials:
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
        return [t.value for t in self._study.trials]

    def get_most_important(self, n_most_important=20):
        importance_values = list(self._importances.values())
        param_names = list(self._importances.keys())
        n_most_important = min(n_most_important, len(self._importances))
        importance_values = importance_values[-n_most_important:]
        param_names = param_names[-n_most_important:]
        return param_names, importance_values

    def plot_importance(self, *, n_most_important=50, map_params=None):
        """
        Plot the importance of parameters
        Most of it based on https://optuna.readthedocs.io/en/stable/_modules/optuna/visualization/_param_importances.html#plot_param_importances

        However, add some functionality we would like to have here
        """
        LOG.info("Plotting importance")
        param_names, importance_values = self.get_most_important(n_most_important)

        if map_params:
            param_names = [map_params[pn] if pn in map_params else pn for pn in param_names]

        figure, ax = plt.subplots(figsize=(30, 10))

        y_pos = [i for i, _ in enumerate(importance_values)]
        ax.barh(y_pos, importance_values)
        ax.set_yticks(y_pos, labels=param_names)
        ax.set_xlabel("parameter importance")

        return figure, ax

    def plot_parallel_coordinates(self, *, n_most_important=20, map_params=None):
        """
        Plot parallel coordinates. Each horizontal line represents a trial, each vertical line a parameter
        """
        LOG.info("Plotting parallel coordinates")
        params, _ = self.get_most_important(n_most_important)

        curves = [[] for _ in self._study.trials]
        losses = self.get_losses()
        skip_trials = []

        for i, trial in enumerate(self._study.trials):
            for param_key in params:
                if param_key not in trial.params:
                    skip_trials.append(i)
                    continue
                curves[i].append(trial.params[param_key])

        # re-map parameter names
        if map_params:
            params = [map_params[pn] if pn in map_params else pn for pn in params]

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
            ax.set_xticks(x_axis[:-1], labels=params, rotation=45)
            ax.set_xlim(x_axis[i], x_axis[i+1])
            ylims = ax.get_ylim()
            ylims_diff = ylims[1] - ylims[1]
            y_low, y_up = (ylims[0] - 0.1 * ylims_diff, ylims[1] + 0.1 * ylims_diff)
            ax.set_ylim(y_low, y_up)
            ax.get_yaxis().set_ticks([y_low, y_up])
            # trick to hide horizontal axis
            ax.spines['bottom'].set_alpha(0)
            ax.spines['top'].set_alpha(0)

        mplcb.ColorbarBase(axes[-1], cmap="Blues_r", norm=norm_colors, label="loss", ticks=[min(losses), max(losses)], )
        figure.subplots_adjust(wspace=0)
        figure.suptitle("Parallel coordinates", fontsize=40)

        return figure, axes

    def plot_slices(self, *, n_most_important=21, map_params=None):
        LOG.info("Plotting slices")
        params, _ = self.get_most_important(n_most_important)

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
        params_labels = params
        if map_params:
            params_labels = [map_params[pn] if pn in map_params else pn for pn in params]

        for param_key, label, ax in zip(params[::-1], params_labels[::-1], axes):
            plot_this = True
            values = []
            for trial in self._study.trials:
                if param_key not in trial.params:
                    plot_this = False
                    break
                values.append(trial.params[param_key])
            if not plot_this:
                continue
            ax.scatter(values, losses, cmap=cmap, norm=norm_colors, c=range(len(losses)))
            ax.set_xlabel(f"value of parameter {label}", fontsize=30)
            ax.set_ylabel("loss", fontsize=30)
            ax.tick_params(labelsize=30)

        for ax in axes[len(params):]:
            ax.set_visible(False)

        figure.suptitle("Loss as function of param values", fontsize=40)

        return figure, axes

    def plot_correlations(self, *, n_most_important=20, map_params=None):
        """
        Plot correlation among parameters
        """
        LOG.info("Plotting parameter correlations")
        params, _ = self.get_most_important(n_most_important)
        params_labels = params
        if map_params:
            params_labels = [map_params[pn] if pn in map_params else pn for pn in params]

        param_values = []
        params_plot = []
        for param_key, label in zip(params[::-1], params_labels[::-1]):
            plot_this = True
            values = []
            for trial in self._study.trials:
                if param_key not in trial.params:
                    plot_this = False
                    break
                values.append(trial.params[param_key])
            if not plot_this:
                continue
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
        figure.suptitle("Parameter correlations over trials", fontsize=40)

        return figure, ax

    def plot_pairwise_scatter(self, *, n_most_important=20, map_params=None):
        """
        Plot correlation among parameters
        """
        LOG.info("Plotting pair-wise scatter")
        params, _ = self.get_most_important(n_most_important)
        params_labels = params
        if map_params:
            params_labels = [map_params[pn] if pn in map_params else pn for pn in params]

        param_values = []
        params_plot = []
        for param_key, label in zip(params[::-1], params_labels[::-1]):
            plot_this = True
            values = []
            for trial in self._study.trials:
                if param_key not in trial.params:
                    plot_this = False
                    break
                values.append(trial.params[param_key])
            if not plot_this:
                continue
            param_values.append(values)
            params_plot.append(label)

        df = pd.DataFrame(list(zip(*param_values)), columns=params_plot)

        # Draw the heatmap with the mask and correct aspect ratio
        ax = sns.pairplot(df, height=1.8, aspect=1.8, plot_kws=dict(edgecolor="k", linewidth=0.5), diag_kind="kde", diag_kws=dict(shade=True),
                          corner=True)
        figure = ax.figure
        figure.set_figheight(30)
        figure.set_figwidth(30)
        figure.suptitle("Pair-wise scatter plot", fontsize=40)

        return figure, ax
