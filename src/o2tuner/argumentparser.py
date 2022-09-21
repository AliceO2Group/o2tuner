"""
Module to process command line arguments
"""


import argparse


class O2TunerArgumentParser(argparse.ArgumentParser):
    """
    Lightweight subclass of ArgumentParser implementing some features required to display the
    o2tuner help: addition of normal arguments and matching between command-line
    options and configuration file options
    """

    def __init__(self):
        # self.args_normal = []
        super().__init__(formatter_class=argparse.RawTextHelpFormatter)
        super().add_argument("-v", "--version", dest="version", default=False, action="store_true",
                             help="Print current o2tuner version on stdout")
        super().add_argument("-w", "--workdir", dest="work_dir", help="Working directory to run in",
                             required=True)
        super().add_argument("-c", "--config", help="your configuration", required=True)
        super().add_argument("-q", "--quiet", dest="quiet", default=False,
                             action="store_true", help="Do not print any message")
        super().add_argument("-d", "--debug", dest="debug", default=None,
                             action="store_true", help="Increase verbosity level")
        super().add_argument("-s", "--stages", nargs="*", help="Run until specified stage")
        super().add_argument("action", default="run",
                             nargs="?", choices=["run", "init"], help="Actions to be performed")

    # def gen_config_help(self, default_conf):
    #     conf_file = os.path.join(os.getcwd(), ".o2tuner-config.yaml")
    #     epilog = f"It is possible to specify the most frequently used options in a YAML " \
    #              f"configuration file in your working directory\n" \
    #              f"Current expected path is: {conf_file}\n" \
    #              f"The following options (along with their default values) can be specified " \
    #              f"(please include `---` as first line):\n---\n"
    #     yaml_lines = {}
    #     longest = 0
    #     for opt in self.args_normal:
    #         if opt.config:
    #             assert opt.config in default_conf, f"option {opt.config} expected in default conf"
    #             optd = {opt.config: default_conf[opt.config]}
    #             yaml_lines[opt.option] = yaml.dump(
    #                 optd, default_flow_style=False).rstrip()
    #             longest = max(longest, len(yaml_lines[opt.option]))
    #     fmt = f"%%-{longest}s  # same as option %%s\n"
    #     for y_line in yaml_lines.items():
    #         epilog += fmt % (yaml_lines[y_line], y_line)

    #     self.epilog = epilog
