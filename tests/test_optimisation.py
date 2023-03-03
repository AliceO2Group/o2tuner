"""
Test optimisation chain
"""
from os.path import exists

from o2tuner.optimise import optimise
from o2tuner.inspector import O2TunerInspector
from o2tuner.utils import annotate_trial


def objective(trial):
    """
    A dummy objective
    """
    x = trial.suggest_float("x", -10, 10)
    y = trial.suggest_float("y", -10, 10)
    annotate_trial(trial, "sum", x + y)
    return (x - 2)**2 + (y - 3)**2


def test_inmemory_optimisation():
    """
    Simple in-memory optimisation
    """
    study_name = "o2tuner_test_study"
    optuna_config = {"study": {"name": study_name},
                     "trials": 100}
    assert optimise(objective, optuna_config, work_dir="./")
    assert exists(f"{study_name}.pkl")


def test_storage_optimisation(needs_sqlite):  # pylint: disable=unused-argument
    """
    Simple optimisation using SQLite storage
    """
    study_name = "o2tuner_test_study"
    storage_filename = "test.db"
    optuna_config = {"study": {"name": study_name, "storage": f"sqlite:///{storage_filename}"},
                     "trials": 100,
                     "jobs": 2}
    assert optimise(objective, optuna_config, work_dir="./")
    assert exists(storage_filename)


def test_full_inmemory_optimisation():
    """
    Full optimisation and inspector chain in-memory
    """
    study_name = "o2tuner_test_study"
    optuna_config = {"study": {"name": study_name},
                     "trials": 100}
    assert optimise(objective, optuna_config, work_dir="./")
    # now resume
    assert optimise(objective, optuna_config, work_dir="./")
    assert exists(f"{study_name}.pkl")
    # now load everything into an inspector
    insp = O2TunerInspector()
    insp.load(optuna_config, "./")
    losses = insp.get_losses()
    # should now have 200 trials
    assert len(losses) == 200
    # check annotations
    annotations = insp.get_annotation_per_trial("sum")
    assert len(annotations) == len(losses)
    assert all(ann is not None for ann in annotations)
    # plot everything we have
    figure, axes = insp.plot_importance()           # pylint: disable=unused-variable
    figure, axes = insp.plot_parallel_coordinates()
    figure, axes = insp.plot_slices()
    figure, axes = insp.plot_correlations()
    figure, axes = insp.plot_pairwise_scatter()
    figure, axes = insp.plot_loss_feature_history()


def test_full_storage_optimisation(needs_sqlite):  # pylint: disable=unused-argument
    """
    Full optimisation and inspector chain using SQLite storage
    """
    study_name = "o2tuner_test_study"
    storage_filename = "test.db"
    optuna_config = {"study": {"name": study_name, "storage": f"sqlite:///{storage_filename}"},
                     "trials": 100,
                     "jobs": 2}
    assert optimise(objective, optuna_config, work_dir="./")
    # now resume
    assert optimise(objective, optuna_config, work_dir="./")
    assert exists(storage_filename)
    # now load everything into an inspector
    insp = O2TunerInspector()
    insp.load(optuna_config, "./")
    losses = insp.get_losses()
    # should now have 200 trials
    assert len(losses) == 200
    # check annotations
    annotations = insp.get_annotation_per_trial("sum")
    assert len(annotations) == len(losses)
    assert all(ann is not None for ann in annotations)
    # plot everything we have
    figure, axes = insp.plot_importance()           # pylint: disable=unused-variable
    figure, axes = insp.plot_parallel_coordinates()
    figure, axes = insp.plot_slices()
    figure, axes = insp.plot_correlations()
    figure, axes = insp.plot_pairwise_scatter()
    figure, axes = insp.plot_loss_feature_history()
