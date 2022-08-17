"""
O2Tuner module
"""


import os
import yaml
from yaml import YAMLError
from o2tuner.log import Log


LOG = Log()


class O2TunerError(Exception):
    """
    O2Tuner error class
    """

    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def __str__(self):
        return self.msg


class O2Tuner(object):
    """
    Steering class for tuning
    """

    def __init__(self, handler) -> None:
        self._handler = handler
        self._conf = {}

    @staticmethod
    def get_default_conf():
        return {"executable": "/bin/true"}

    def parse_config(self):
        conf_file = os.path.join(os.path.expanduser("~"),
                                 ".o2tuner-config.yaml")
        try:
            with open(conf_file, encoding="utf8") as conf_file_data:
                conf_override = yaml.safe_load(conf_file_data)
                for k in self._conf:
                    self._conf[k] = conf_override.get(k, self._conf[k])
        except (OSError, IOError, YAMLError, AttributeError):
            pass

    def override_config(self, override):
        if not override:
            return
        for k in self._conf:
            if not override.get(k) is None:
                self._conf[k] = override[k]

    def reset_handler(self, handler):
        self._handler = handler

    def init(self, **kwargs):
        self._handler.initialise(**kwargs)

    def run(self):
        self._handler.optimise()
