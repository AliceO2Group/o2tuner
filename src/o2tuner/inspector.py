"""
Mainstream and custom backends should be placed here
"""
from os.path import join
import matplotlib.pyplot as plt

import optuna.visualization.matplotlib as ovm

from o2tuner.io import parse_yaml, make_dir
from o2tuner.utils import load_or_create_study
from o2tuner.sampler import construct_sampler


class OptunaInspector:  # pylint: disable=too-few-public-methods
    """
    Inspect optuna study
    """

    def __init__(self, config_path=None):
        """
        Constructor
        """
        self._study = None
        self._config_path = config_path
        self._config = None

    def load_impl(self, config_path):
        """
        Implementation of loading a study
        """
        config = parse_yaml(config_path)
        sampler = construct_sampler(config.get("sampler", None))
        storage = config.get("study", {})
        self._study = load_or_create_study(storage.get("name"), storage.get("storage"), sampler)
        self._config = config

    def load(self, config_path=None):
        """
        Loading wrapper
        """
        if not config_path and not self._config_path:
            print("WARNING: Nothing to load, no configuration given")
            return False
        if config_path:
            self.load_impl(config_path)
        else:
            self.load_impl(self._config_path)
        return True

    def visualise(self, out_dir=None):
        """
        Doing a simple visualisation using optuna's built-in functionality
        """
        if not self._study:
            print("WARNING: No study loaded to visualise")
            return

        out_dir = out_dir or join(self._config.get("workdir", "./"), "visualisation")
        make_dir(out_dir)

        def to_figure_and_save(axis, path):
            fig = plt.figure()
            axis.figure = fig
            fig.add_axes(axis)
            fig.savefig(path)
            plt.close(fig)

        ax_plot_optimization_history = ovm.plot_optimization_history(self._study)
        to_figure_and_save(ax_plot_optimization_history, join(out_dir, "ax_plot_optimization_history.png"))
        ax_plot_parallel_coordinate = ovm.plot_parallel_coordinate(self._study)
        to_figure_and_save(ax_plot_parallel_coordinate, join(out_dir, "ax_plot_parallel_coordinate.png"))
        ax_plot_param_importances = ovm.plot_param_importances(self._study)
        to_figure_and_save(ax_plot_param_importances, join(out_dir, "ax_plot_param_importances.png"))
