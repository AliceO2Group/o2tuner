# Cut tuning for O2 (target GEANT4)
This directory contains all necessary tools/scripts to run a full cut optimisation
* reference and baseline (under testing),
* optimisation (under testing),
* evaluation (under testing),
* closure (to be implemented).

**NOTE:** So far this provides more the proof-of-principle functionality rather than an actual optimisation that can be used for production!

In the following it is also assumed that your `o2tuner` python package is located at `$O2TUNER`.

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
python $O2TUNER/src/o2tuner_run/cut_tuning_optimise.py -c <workdir>/optuna_config.yaml -u <workdir>/cut_tuning_config.yaml
```

## Evaluation (under testing)
The evaluation step is meant to give the user some insight into properties of parameters, their value distributions, evolutions, correlations and importances.
```bash
python $O2TUNER/src/o2tuner_run/cut_tuning_evaluate.py -c <workdir>/optuna_config.yaml [-u <path/to/user_config>] [-o <output/for/plots>]
```

## Closure (not yet implemented)
**This will be based on the O2DPG RelVal**
