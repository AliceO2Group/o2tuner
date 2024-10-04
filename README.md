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
# </path/to>/config.yaml
stages_optimisation:
    optimisation:
        file: optimisation.py
        objective: objective
```

Assuming both files are in the same directory, simply run
```bash
o2tuner -w <my_work_dir> -c </path/to>/config.yaml
```

Please also check out some [tests](tests/test_full) if you want to have an impression of some working code, its configuration and definitions.

## Configuration

### Structure
The configuration, containing both a global static configuration dictionary as well as the definition of which python functions or command lines should be run, is defined inside a `yaml` file.
The overall structure looks like
```yaml
# config.yaml

config:
  # global static configuration dictionary

stages_user:
  # dictionary to define custom user stages, e.g. to evaluate optimisation runs

stages_optimisation:
  # dictionary to define optimisations
```
All top-level keys are optional. However, having neither `stages_optimisation` nor `stages_user`, there is nothing to run of course.


### Define user stages
User stages are defined under the top-level key `stages_user`. Such a stage is particularly useful to evaluate optimisation runs. Another use case could be some necessary pre-processing before an optimisation could be run.
An example may look like
```yaml
stages_user: # top-level key, some pre-processing
  pre_proc1:
    python:                                  # run some python code
      file: pre_proc.py
      entrypoint: some_func                  # the function inside the pre_proc.py file to call
    cwd: different_name_of_working_directory # optional; if not set, the name of the stage (in this case "pre_proc1") is given to the working directory
    log_file: different_log_file_name        # optional; if not set, the name "log.log" is used
    config:                                  # optional; can be used to add something or to override key-values in the global static configuration (locally, only for this stage)
      another_key: another_value

  pre_proc2:
    # definition...
    # this is assumed to be independent of any other stage
  
  pre_proc3:
    # definition...
    deps:                                    # mark this stage to depend on pre_proc1 and pre_proc2
      - pre_proc1
      - pre_proc2
```

### Define optimisation stages
The definition of optimisation stages are very similar to the user stages. For instance
```yaml
stages_user:
  # as above
  # one additional stage that will be used to create some evaluation plots on top of an optimisation
  evaluate:
    file: evaluate.py
    entrypoint: evaluate_default
    # config or cwd or log_file
    optimisations:                           # list of optimisations to be processed (opt1 definition below)
      - opt1

stages_optimisation:
  opt1:
    file: optimisation.py
    entrypoint: objective1
    # config or cwd or log_file, optional
    deps:
      - pre_proc3
    # here some specific keys, all optional
    jobs: 3                                  # optional; number of parallel jobs to run, in this case 3, default is 1
    trials: 100                              # optional; number of optimisation trials, in this case 100; will be distributed to the parallel jobs
    # optuna-specific settings
    study:
      name: different_name_of_study          # optional; default is the name of the stage, in this case "opt1"
      storage: sqlite:///opt.db              # optional; default is sqlite:///o2tuner_study.db, note that the same DB might be used for different optimisation stages. In there, different studies could be saved under their different names
    sampler:                                 # optional; advanced, usually not needed; default is tpe with its default args
      name: tpe                              # tree-parzen estimator
      args:                                  # see https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html for possible arguments of TPE sampler
        constant_liar: true
        n_startup_trials: 40
```


### Global static configuration
Each python function that is defined by the user will see the dictionary under the top-level `config` key. This makes it possible to share specific settings, paths, names etc. among all stages.
```yaml
# config.yaml

config:
  key1: value1
  key2: value2
  key3:
    key3_1: value3_1
    key3_2: value3_2
    key3_3:
      - value3_3_1
      - value3_3_2
      - value3_3_3
  # ...

# ...
```
Per stage, it will be extended by what is found under the optional local `config` key. If there are keys with the same name, the ones defined in a stage take precedence *in that stage*.

## The python part
First of all: All python files that are referred to in the above configuration example should be located in one common directory.

### User stages (no processing any optimisation output)
Coming back to the definition of e.g. `pre_proc1` in the above configuration example, a python function may look like
```python
# pre_proc.py
def some_func(config):
  # do whatever needs to be done
  some_value = config['another_key'] # this value might be needed for something
  # if anything goes wrong at any point, return False

  # return True to mark success of that function
  return True
```
The `config` argument is exactly the [global static configuration](#global-static-configuration) (with extended/overriden parameters, see [User stages](#define-user-stages)).
Also note that the function is executed inside the defined `cwd` (would be `pre_proc1` given the [above definition](#define-user-stages)). So if that stage produces any artifacts, they will be written inside this directory.

### User stages (processing optimisation output)
Coming back to the definition of e.g. `evaluate` in the above configuration example, a python funtion may look like
```python
# evaluate.py
def evaluate_default(inspectors, config):
  # do whatever needs to be done
  # get a certain value from the config
  value3_3_3 = config['key3']['key3_3'][2]
  # if anything goes wrong at any point, return False

  # return True to mark success of that function
  return True
```
The `inspectors` argument is a list of `O2TunerInspector` objects, see [below](#inspector). It brings in various results of the optimisation [opt1](#define-optimisation-stages).

### Optimisation stages
Coming back to the definition of e.g. `opt1` in the above configuration example, a python funtion may look like
```python
# optimisation.py

@needs_cwd # optional; to indicate if each trial should be executed in its own sub-directory, can 
# optional decorator, if the objective function only returns one value and if that value should be minimised;
# required, if one value should be maximised OR if more than one value is returned
# in this example, the first value should be minimised, the other maximised ==> multi-objective optimisation
@directions(['minimize', 'minimize'])
def objective1(trial, config):
  # do whatever needs to be done
  # see e.g. https://optuna.readthedocs.io/en/stable/tutorial/10_key_features/002_configurations.html
  return value_to_minimise, value_to_maximise
```

#### Annotate each trial with additional information
It might be necessary or desired to not only receive some values of the objective function during an evaluation but to also be able to have quick access to other information, e.g. some that the computation is based on.
For instance, one might change something in the global config at some point. But to make some information persistent and link it to a trial, 

```python
from o2tuner.utils import annotate_trial

def objective(trial, config):
    x = trial.suggest_float(0, config['upper_x'])
    y = trial.suggest_float(-5, config['upper_y'])
    
    annotate_trial(trial, 'upper_x', config['upper_x'])
    annotate_trial(trial, 'upper_y', config['upper_y'])
    annotate_trial(trial, "other_key", "another meaningful info")

    return (x - 0.5)**2 + x**4
```

## Run
On the shoulders of the above example, the optimisation can be run like
```bash
o2tuner -w <my_work_dir> -c </path/to>/config.yaml -s opt1
```
Everything runs inside `<my_work_dir>` to keep other directories clean. Working directories of the individual stages will be created inside that `<my_work_dir>`.
`o2tuner` is told to run the stage `opt1`. It will therefore make sure that all dependent stages are run before or have been run already. If you want to run another stage again although it has been done already, one can run
```bash
o2tuner -w <my_work_dir> -c </path/to>/config.yaml -s opt1 pre_proc2
```
The `-c` argument gets the path to where the `config.yaml` is actually located. It is assumed that in that same directory, the code can also find the python files (in this example these would be `pre_proc.py`, `optimisation.py` and `evaluate.py`).
If the python files are located in a different directory, `--script-dir <path/to/script_dir>`.


### Abort/continue an optimisation
Assume you are running an optimisation, but while it runs you realise, it is for instance not converging or there might be another problem. In such a case, one can hit `Ctrl-\` to send a `SIGQUIT` to `o2tuner`. It will tell it to return from the optimisation but finalising what has been done so far.
**NOTE** that is is still a bit fragile and it might happen that the code does not correctly shut down the optimisation processes. However, it has not been seen that this would corrupt the optimisation database file (in the present example `opt.db`).

On the other hand, if there is an optimisation which has been run for a few trials already, it can be continued and therefore extended by simply invoking
```bash
o2tuner -w </my_work_dir> -c </path/to>/config.yaml -s opt1
```
This will again run as many trials as defined in the configuration. If one only wants to add a few more trials, it has to be specified in the `config.yaml`.

## Inspector
Have another look at the `evaluate` stage from [above](#define-optimisation-stages). It expects `opt1` under the `optimisations` key.
This implies two things:
1. `opt1` will be treated as a dependency,
1. each of these optimisation results (here only one optimisation) will be passed in a list of `O2TunerInspector` objects.

So we will find one `O2TunerInspector` object and can use it:
```python
#evaluate.py

def evaluate(inspectors, config):
    # only one optimisation
    insp = inspectors[0]
    # print losses of all successful trials
    losses = insp.get_losses()
    print(losses)

    # check annotations
    annotations = insp.get_annotation_per_trial("other_key")
    # plot everything we have
    figure, axes = insp.plot_importance()
    # do something with axes or figure, e.g. save
    figure, axes = insp.plot_parallel_coordinates()
    figure, axes = insp.plot_slices()
    figure, axes = insp.plot_correlations()
    figure, axes = insp.plot_pairwise_scatter()
    figure, axes = insp.plot_loss_feature_history()
```

Of course, one can do whatever should be done with the optimisation results.
