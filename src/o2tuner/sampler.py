"""
Construct and manage samplers
"""
import sys
# NOTE: There are more sampler implemented in optuna, however, let's start with these
from optuna.samplers import BaseSampler, GridSampler, RandomSampler, TPESampler, NSGAIISampler
from o2tuner.log import get_logger

LOG = get_logger()


# our current dictionary of sampler; eventually we might just support all of the ones available in optuna
SAMPLERS = {"base": BaseSampler,
            "grid": GridSampler,
            "random": RandomSampler,
            "tpe": TPESampler,
            "genetic": NSGAIISampler}


def construct_sampler(sampler_config=None):
    """
    Construct a smapler from potential custom configuration
    """
    if not sampler_config:
        return TPESampler()
    name = sampler_config.get("name").lower()
    if name not in SAMPLERS:
        LOG.error("Unknwon sampler %s", name)
        sys.exit(1)
    # NOTE Only YAMLable arguments can be used for this of course. We need to find a way to pass more complex things.
    #      E.g. some samplers take lambda function/callables etc.
    args = sampler_config.get("args", {})
    return SAMPLERS[name](**args)
