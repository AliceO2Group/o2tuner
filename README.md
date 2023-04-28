# o2tuner
![](https://github.com/mconcas/o2tuner/actions/workflows/pythonpackage.yml/badge.svg)
![](https://github.com/mconcas/o2tuner/actions/workflows/codeql.yml/badge.svg)
![](https://github.com/mconcas/o2tuner/actions/workflows/pythonpublish.yml/badge.svg)

This package contains a tool for optimising routines such as executables, python scripts, ML algorithms etc.
The basic idea is: Whenever something depends on some parameters, these might provide a handle to optimise a certain algorithm.

Although not limited to it, this project was started with a focus on algorithms included in [ALICE O2](https://github.com/AliceO2Group/AliceO2).

In addition to the pure optimisation, a workflow can contain preparatory as well as evaluation steps. A workflow or "recipe" definition helps to make the whole optimisation procedure modular and easily reproducible.

`o2tuner` is built on the shoulders of [`optuna`](https://github.com/optuna/optuna), so if you have used that already, a few things might look familiar.

## Build

### Using `pip`
Simply do
```bash
pip install o2tuner
```

### From source
```bash
# Change to where you want to checkout the repository
cd ${INSTALLDIR}
# Clone it there
git clone git@github.com:AliceO2Group/o2tuner.git
# Move into the directory
cd o2tuner
# Install...
pip install -e .
```

### Verify the setup
1. Install [`pytest`](https://pypi.org/project/pytest/)
1. `${INSTALLDIR}/o2tuner/run_tests.sh pytest`

In addition, you can try to run
```bash
o2tuner --help
```
to see if the entrypoint was correctly created.

## Quick example
For the most basic example, one could think of an objective defined in a python file `optimisation.py` like this

```python
# optimisation.py

def objective(trial):
    x = trial.suggest_float(0, 1)
    y = trial.suggest_float(-5, 5)

    return (x - 0.5)**2 + x**4
```

In addition, there must be a configuration file such as
```yaml
stages_optimisation:
    optimisation:
        file: optimisation.py
        objective: objective
```

Assuming both files are in the same directory, simply run
```bash
o2tuner -w </my_work_dir> -c </path/to>/config.yaml
```

## The optimisation

## Defining the objective function
The objective is the central piece of code to be implemented. The only requirements are
1. It needs to return a scalar value,
1. the signature must be either `func(trial)` or `func(trial, config)`.

The first scenario is basically the way to define an objective as one would do in the pure `optuna` case. On the other hand, `o2tuner` is able to pipe in a static config which can be accessed at runtime. To do so, change `config.yaml` to
```yaml
stages_optimisation:
    optimisation:
        file: optimisation.py
        objective: objective
        config:
            parameter1: value1
            parameter2: value2
```
and in the objective function you can access the configuration dictionary.

### When your algorithm produces artifacts
Let's take an example from particle physics and assume the aim is to optimise a detector simulation algorithm. In that case, the algorithm might leave various files after execution (such as particle kinematics, created hits, logs etc.). This will happen for each trial during the optimisation. Of course, you do not want to mix artifacts from different trials, in particular if you need to access certain files in a later stage. Therefore, the objective can be decorated
```python
@needs_cwd
def objective(trial):
    # your implementation
```
By doing so, each trial will be executed in its own dedicated working directory.

### When you have a preparation stage
If you need some data to start your optimisation from, it might be nice to make the optimisation workflow more self-consistent and add a stage at the very beginning to create the data or copy it from somewhere. That introduces a dependency which can be reflected in the configuration using the `deps` key
```yaml
stages_user:
    preparation:
    # a data preparation stage
    cmd: cp -r <from_somewhere>/* .

stages_optimisation:
    optimisation:
        file: optimisation.py
        objective: objective
    deps:
        - preparation
```
This will make sure, that the `preparation` stage will be run before the optimisation stage.

### When you want to access some data
Sticking to the data preparation example, you might want to access some of that data in you objective function. The only thing you need to know is the corresponding working directory which in this case would be `preparation`. So, what you can do is
```python
from o2tuner.config import resolve_path

def objective(trial):
    x = trial.suggest_float(0, 1)
    y = trial.suggest_float(-5, 5)

    full_path = resolve_path("preparation")
    print(full_path)

    return (x - 0.5)**2 + x**4
```
Of course, instead of just printing the full path, you can now actually access files under that directory without knowing **where exactly** it is located.

### Running multiple optimisation processes in parallel
`optuna` allows parallel execution of multiple optimisation processes. The processes (and for instance the samplers in each process) communicate via some database. The default is to use `SQLite`. If nothing particular is specified in the configuration, it will be tried to run the optimisation that way and by default, one process will be spawned. Instead of `SQLite` one could as well use `MySQL`. If `o2tuner` finds that this is not possible, it will abort.
If you do not want to use any kind of database, you can attempt a simple in-memory run. The you need to explicitly state that you want to run one single job. You can do so with
```yaml
stages_optimisation:
    optimisation:
        file: optimisation.py
        objective: objective
    jobs: 1
    deps:
        - preparation
```

### More or less the full optimisation configuration
The most complex an optimisation configuration might look like at the moment would be

```yaml
stages_user:
    preparation:
    # a data preparation stage
    cmd: cp -r <from_somewhere>/* .

stages_optimisation:
    optimisation:
        file: optimisation.py
        objective: objective
    # number of parallel jobs to run
    jobs: 10
    # how many trials to do in total (distributed to number of workers/jobs)
    trials: 600
    # specify a sampler. tpe will anyway be used by default. This is to show how one can configure it further
    sampler:
        name: tpe
        args:
            constant_liar: True
            n_startup_trials: 150
    deps:
        - preparation
    config:
        parameter1: value1
        parameter2: value2
```

### If you want to abort/continue an optimisation
Assume you are running an optimisation, but while it runs you realise, it is for instance not converging or there might be another problem. In such a case, one can hit `Ctrl-\` to send a `SIGQUIT` to `o2tuner`. It will tell it to return from the optimisation but finalising what has been done so far.

On the other hand, if there is an optimisation which has been run for a few trials already, it can be continued by simply invoking
```bash
o2tuner -w </my_work_dir> -c </path/to>/config.yaml - s optimisation
```
With the `--stages/-s` flag, stages can be explicitly rerun/continued.

### Save further information
Sometimes you might want to keep some other information for each trial of an optimisation. It is therefore possible to annotate a trial with key-value pairs. Note, that it must be possible to serialise the annotations to `JSON` format. But most importantly, it is possible to annotate with all kinds of text, numbers, lists, and dictionaries thereof. This is done as follows
```python
from o2tuner.utils import annotate_trial

def objective(trial):
    x = trial.suggest_float(0, 1)
    y = trial.suggest_float(-5, 5)

    annotate_trial(trial, "key", "something meaningful")

    return (x - 0.5)**2 + x**4
```
These annotations can be recovered later as you will see below. For instance, if there are some intermediate values which were used to calculate the loss, it might be interesting to save those for later inspection.

## Other than optimising

### Inspect, evaluate, plot
If you want to explore what happened during an optimisation, you can define another stage to do so. We assume, that your optimisation stage is called `optimisation`. In the config under `stages_user`, add something like
```yaml
stages_user:
    evaluate:
        python: evaluate.py
        entrypoint: evaluate
    optimisations:
        - optimisation
    config:
        parameter1: value1
        parameter2: value2
```
This does two things: First, `optimisation` will be automatically a dependency of this `evaluate` task. Secondly, it will pass in a list of so-called `O2TunerInspector`s. In this case we are referring to a python function `evaluate` in a script `evaluate.py` (of course, one can also just throw all functions into one single python file). This function must have the signature `func(inspectors, config)` and this first argument is exactly what will be populated. `config` might be `None` if nothing was given, however in the above example, there is some static configuration.

So we will find one `O2TunerInspector` object and can use it:
```python
#evaluate.py

def evaluate(inspectors, config):
    # for convenience
    insp = inspectors[0]
    # print losses of all successful trials
    print(insp.get_losses())

    # extracting some annotation
    annotations = insp.get_annotation_per_trial("key")
    print(annotations)

    # plot the history of features/parameter values and the loss as a function of trials
    fig, _ = insp.plot_loss_feature_history()
    fig.savefig("loss_feature_history")
```
