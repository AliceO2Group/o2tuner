"""
Module to process command line arguments
"""


import os.path
import argparse
from collections import namedtuple
from click import option
import yaml

O2TunerArg = namedtuple("O2TunerArg", "option config descr")


class O2TunerArgumentParser(argparse.ArgumentParser):
    """
    Lightweight subclass of ArgumentParser implementing some features required to display the
    o2tuner help: addition of normal arguments and matching between command-line
    options and configuration file options
    """

    def __init__(self):
        self.args_normal = []
        super().__init__(formatter_class=argparse.RawTextHelpFormatter)

    def add_argument(self, *args, **kwargs):
        config_var = None
        if kwargs.get("config", False):
            config_var = kwargs["dest"]
            kwargs["help"] = kwargs.get("help", "") + " [" + config_var + "]"

        self.args_normal.append(O2TunerArg(
            args[0], config_var, kwargs.get("help", "")))
        return self.add_argument(*args, **kwargs)

    def gen_config_help(self, default_conf):
        conf_file = os.path.join(
            os.path.expanduser("~"), ".o2tuner-config.yaml")  # make it cwd
        epilog = f"it is possible to specify the most frequently used options in a YAML " \
                 f"configuration file in {conf_file}\n" \
                 f"the following options (along with their default values) can be specified " \
                 f"(please include `---` as first line):\n---\n".format(conf_file=conf_file)
        yaml_lines = {}
        longest = 0
        for opt in self.args_normal:
            if opt.config:
                assert opt.config in default_conf, f"option {option} expected in default conf".format(
                    option=opt.config)
                optd = {opt.config: default_conf[opt.config]}
                yaml_lines[opt.option] = yaml.dump(
                    optd, default_flow_style=False).rstrip()
                longest = max(longest, len(yaml_lines[opt.option]))
        fmt = f"%%-{longest}s  # same as option %%s\n".format(longest=longest)
        for y_line in yaml_lines.items():
            epilog += fmt % (yaml_lines[y_line], y_line)

        self.epilog = epilog
