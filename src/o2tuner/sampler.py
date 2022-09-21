"""
Construct and manage samplers
"""
import sys
# NOTE: There are more sampler implemented in optuna, however, let's start with these
from optuna.samplers import BaseSampler, GridSampler, RandomSampler, TPESampler, NSGAIISampler
from o2tuner.log import Log

LOG = Log()


SAMPLERS = {"base": BaseSampler,
            "grid": GridSampler,
            "random": RandomSampler,
            "tpe": TPESampler,
            "genetic": NSGAIISampler}


def construct_sampler(sampler_config=None):
    if not sampler_config:
        return TPESampler()
    name = sampler_config.get("name").lower()
    if name not in SAMPLERS:
        LOG.error(f"Unknwon sampler {name}")
        sys.exit(1)
    # NOTE Only YAMLable arguments can be used for this of course. We need to find a way to pass more complex things.
    #      E.g. some samplers take lambda function/callables etc.
    args = sampler_config.get("args", {})
    return SAMPLERS[name](**args)
