"""
Configuration functionality and parsing
"""
import sys
import dataclasses
from os.path import join, basename, abspath
from glob import glob
from copy import deepcopy

from o2tuner.io import make_dir, parse_yaml, exists_dir
from o2tuner.log import Log


@dataclasses.dataclass
class WorkDir:
    """
    Use this object to set the working directory globally
    """
    path = None


WORK_DIR = WorkDir()

LOG = Log()

CONFIG_STAGES_USER_KEY = "stages_user"
CONFIG_STAGES_OPTIMISATION_KEY = "stages_optimisation"
CONFIG_STAGES_EVALUATION_KEY = "stages_evaluation"

CONFIG_STAGES_KEYS = [CONFIG_STAGES_USER_KEY, CONFIG_STAGES_OPTIMISATION_KEY, CONFIG_STAGES_EVALUATION_KEY]


def get_work_dir():
    return WORK_DIR.path


def resolve_path(rel_cwd):
    return join(WORK_DIR.path, rel_cwd)


def get_done_dir():
    return join(WORK_DIR.path, "o2tuner_done")


class Configuration:
    """
    Class to manage user configurations centrally
    """
    def __init__(self, user_config, script_dir=None):
        self.user_config_dict = parse_yaml(user_config) if isinstance(user_config, str) else user_config
        # We could do a deepcopy now here in order to do some internal adjustments. However, there still seem to be references left in the
        # copied dictionary which seems to be rather weird. See also the long comment below.
        self.script_dir = script_dir
        self.all_stages = None
        if not self.setup():
            sys.exit(1)

    def setup(self):
        """
        * Set working directories if not specified explicitly by the user
        * Several sanity checks of configuration
        """
        config = self.user_config_dict
        # We require at least one of the stages
        if CONFIG_STAGES_USER_KEY not in config and CONFIG_STAGES_OPTIMISATION_KEY not in config and CONFIG_STAGES_EVALUATION_KEY not in config:
            LOG.error("At least one of the stages needs to be there:")
            print(f"  - {CONFIG_STAGES_USER_KEY}\n  - {CONFIG_STAGES_OPTIMISATION_KEY}/n  - {CONFIG_STAGES_EVALUATION_KEY}")
            sys.exit(1)

        self.all_stages = []
        # set working directories
        all_deps = []
        has_error = False
        for csk in CONFIG_STAGES_KEYS:
            if csk not in config:
                continue
            for name in config[csk]:
                # I am not sure yet why we have to a deepcopy here. If we do it on the whole dictionary, there seem to be references left still
                # which seems weird. That has to be understood.
                # So when not doing this here, it can happen that - if certain stages below share the same references - we don't see what we expect,
                # in particular when adjusting file paths etc.
                config[csk][name] = deepcopy(config[csk][name])
                value = config[csk][name]
                value["cwd"] = value.get("cwd", name)
                value["config"] = value.get("config", {})
                all_deps.extend(value.get("deps", []))

                if csk in (CONFIG_STAGES_OPTIMISATION_KEY, CONFIG_STAGES_EVALUATION_KEY):
                    if "file" not in value or ("objective" not in value and "entrypoint" not in value):
                        LOG.error(f"Need \"file\" as well as \"objective\"/\"entrypoint\" for optimisation stage {name}")
                        has_error = True
                        continue
                    value["entrypoint"] = value.get("entrypoint", value.get("objective"))
                    value["file"] = join(self.script_dir, value["file"])

                if csk == CONFIG_STAGES_OPTIMISATION_KEY:
                    optuna_config = {k: v for k, v in value.items() if k not in ("entrypoint", "file", "config")}
                    optuna_config["study"] = optuna_config.get("study", {"name": name})
                    optuna_config["study"]["name"] = optuna_config["study"].get("name", name)
                    value["optuna_config"] = optuna_config

                if csk == CONFIG_STAGES_EVALUATION_KEY:
                    if "optimisations" not in value:
                        LOG.error(f"Need key \"optimisations\" to know which optimisations to load in {name}")
                        has_error = True
                        continue

                if csk == CONFIG_STAGES_USER_KEY:
                    if "cmd" not in value and "python" not in value:
                        LOG.error(f"Need either the \"cmd\" or \"python\" section in the config of {name}")
                        has_error = True
                        continue

                    if python_dict := value.get("python", None):
                        if "file" not in python_dict or "entrypoint" not in python_dict:
                            LOG.error(f"Need \"file\" as well as \"entrypoint\" for user stage {name}")
                            has_error = True
                            continue
                        # See long comment above. E.g. here could be problems if we don't deepcopy
                        # (but again, we cannot deepcopy the overall self.user_config_dict
                        value["python"]["file"] = join(self.script_dir, value["python"]["file"])

                self.all_stages.append((name, value, csk))

        all_stages_names = [stage[0] for stage in self.all_stages]
        for dep in all_deps:
            if dep not in all_stages_names:
                LOG.error(f"Unknown dependency {dep}")
                has_error = True
                continue

        return not has_error

    def get_stages(self, stage_key):
        """
        Get stages for given key
        """
        if stage_key not in CONFIG_STAGES_KEYS:
            LOG.error(f"Unknown stage key {stage_key}")
            sys.exit(1)
        return {stage[0]: stage[1] for stage in self.all_stages if stage[2] == stage_key}

    def get_stages_optimisation(self):
        """
        Helper to get optimisation stages
        """
        return self.get_stages(CONFIG_STAGES_OPTIMISATION_KEY)

    @staticmethod
    def set_work_dir(work_dir):
        WORK_DIR.path = abspath(work_dir)

    @staticmethod
    def prepare_work_dir():
        make_dir(WORK_DIR.path)
        o2tuner_done_dir = get_done_dir()
        make_dir(o2tuner_done_dir)

    @staticmethod
    def get_stages_done():
        done_dir = get_done_dir()
        done_files = glob(f"{done_dir}/DONE_*")
        done = []
        for done_file in done_files:
            with open(done_file, "r", encoding="utf-8") as this_done:
                cwd_rel = this_done.readline().strip()
                if not exists_dir(join(WORK_DIR.path, cwd_rel)):
                    continue
            done.append(basename(done_file)[5:])
        return done

    @staticmethod
    def set_stage_done(name, rel_cwd):
        done_dir = get_done_dir()
        done_file = join(done_dir, f"DONE_{name}")
        with open(done_file, "w", encoding="utf-8") as done:
            done.write(rel_cwd)
