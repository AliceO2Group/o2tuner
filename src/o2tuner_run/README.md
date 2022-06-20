# Cut tuning for O2 (target GEANT4)
This directory contains all necessary tools/scripts to run a full cut optimisation
* reference and baseline (under testing),
* optimisation (under testing),
* evaluation (preliminary),
* closure (to be implemented).

**NOTE:** So far this provides more the proof-of-principle functionality rather than an actual optimisation that can be used for production!

## Reference and baseline (under testing)
A reference run is steered with
```bash
python $O2TUNER/src/o2tuner_run/cut_tuning_reference.py [-d <workdir>]
```
This should run out of the box. Type `--help` to see the full help message. The optional `-d` option specifies where the artifact of the reference and baseline run are dumped to (default is `./`). In addition you will find a configuration at `<workdir>/cut_tuning_config.yaml`. You do not have to edit anything here actually.
In addition you will find a pre-configuration for `optuna` at `<workdir>/optuna_config.yaml` with some additional comments inside. If you only want to check out the optimisation run in general, also this on is good to go.
So we can go directly to the optimisation step!

## Optimisation (under testing)
Run the optimisation with
```bash
python $O2TUNER/src/o2tuner_run/cut_tuning_optimisation.py -c <workdir>/optuna_config.yaml -u <workdir>/cut_tuning_config.yaml
```

## Evaluation (under development)
A simple evaluation using some of the `optuna`'s visualisation tools can be achieved with
```bash
python $O2TUNER/src/o2tuner_run/cut_tuning_evaluation.py -c <workdir>/optuna_config.yaml
```
Note, however, that due to the number of parameters, some of these plots are not yet very useful.

## Closure (not yet implemented)
