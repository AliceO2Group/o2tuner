"""
Configuration functionality and parsing
"""
import sys
import dataclasses
from os.path import join, basename, abspath
from glob import glob
from copy import deepcopy

from o2tuner.io import make_dir, parse_yaml, exists_dir
from o2tuner.log import get_logger


@dataclasses.dataclass
class WorkDir:
    """
    Use this object to set the working directory globally
    """
    path = None


WORK_DIR = WorkDir()

LOG = get_logger()

CONFIG_STAGES_USER_KEY = "stages_user"
CONFIG_STAGES_OPTIMISATION_KEY = "stages_optimisation"

CONFIG_STAGES_KEYS = [CONFIG_STAGES_USER_KEY, CONFIG_STAGES_OPTIMISATION_KEY]


def get_work_dir():
    """
    Simply return the parent workdir
    """
    return WORK_DIR.path


def resolve_path(rel_cwd):
    """
    Resolve a relative path to find it inside the current parent workdir
    """
    return join(WORK_DIR.path, rel_cwd)


def get_done_dir():
    """
    Get the directory where finished tasks are noted
    """
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
            # simply exit, the errors should have been printed by setup()
            sys.exit(1)

    def setup_optimisation_stage(self, name, value):
        """
        Setup an optimisation stage
        """
        if "file" not in value or ("entrypoint" not in value and "objective" not in value):
            LOG.error("Need \"file\" as well as \"objective\" or \"entrypoint\" for optimisation stage %s", name)
            return False
        value["file"] = join(self.script_dir, value["file"])
        value["entrypoint"] = value.get("entrypoint", value["objective"])

        optuna_config = {k: v for k, v in value.items() if k not in ("entrypoint", "file", "config")}
        optuna_config["study"] = optuna_config.get("study", {"name": name})
        optuna_config["study"]["name"] = optuna_config["study"].get("name", name)
        value["optuna_config"] = optuna_config

        return True

    def setup_user_stage(self, name, value):
        """
        Setup a user stage
        """
        if "cmd" not in value and "python" not in value:
            LOG.error("Need either the \"cmd\" or \"python\" section in the config of %s", name)
            return False

        if python_dict := value.get("python", None):
            if "file" not in python_dict or "entrypoint" not in python_dict:
                LOG.error("Need \"file\" as well as \"entrypoint\" for user stage %s", name)
                return False
            # See long comment above. E.g. here could be problems if we don't deepcopy
            # (but again, we cannot deepcopy the overall self.user_config_dict
            value["python"]["file"] = join(self.script_dir, value["python"]["file"])

            # let's see if any optimisation are requested (which will eventually passed in via O2Inspectors)
            if "optimisations" in value:
                user_deps = value.get("deps", [])
                for opt in value["optimisations"]:
                    if opt in user_deps:
                        continue
                    user_deps.append(opt)
                value["deps"] = user_deps
            return True

        if "optimisation" in value:
            # Not running a python script, but optimisation specified, but we cannot make use of this functionality in shell
            LOG.error("Since not executing a python script in stage %s, cannot make use of what is specified under \"optimisations\" key", name)
            return False

        return True

    def setup(self):
        """
        * Set working directories if not specified explicitly by the user
        * Several sanity checks of configuration
        """
        config = self.user_config_dict
        # We require at least one of the stages
        if CONFIG_STAGES_USER_KEY not in config and CONFIG_STAGES_OPTIMISATION_KEY not in config:
            LOG.error("At least one of the stages needs to be there:")
            print(f"  - {CONFIG_STAGES_USER_KEY}\n  - {CONFIG_STAGES_OPTIMISATION_KEY}")
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

                if csk == CONFIG_STAGES_OPTIMISATION_KEY:
                    has_error = not self.setup_optimisation_stage(name, value) or has_error

                if csk == CONFIG_STAGES_USER_KEY:
                    has_error = not self.setup_user_stage(name, value) or has_error

                self.all_stages.append((name, value, csk))

        all_stages_names = [stage[0] for stage in self.all_stages]
        for dep in all_deps:
            if dep not in all_stages_names:
                LOG.error("Unknown dependency %s", dep)
                has_error = True
                continue

        return not has_error

    def get_stages(self, stage_key):
        """
        Get stages for given key
        """
        if stage_key not in CONFIG_STAGES_KEYS:
            LOG.error("Unknown stage key %s", stage_key)
            sys.exit(1)
        return {stage[0]: stage[1] for stage in self.all_stages if stage[2] == stage_key}

    def get_stages_optimisation(self):
        """
        Helper to get optimisation stages
        """
        return self.get_stages(CONFIG_STAGES_OPTIMISATION_KEY)

    @staticmethod
    def set_work_dir(work_dir):
        """
        Set the current parent workdir
        """
        WORK_DIR.path = abspath(work_dir)

    @staticmethod
    def prepare_work_dir():
        """
        Create current workdir structure
        """
        make_dir(WORK_DIR.path)
        o2tuner_done_dir = get_done_dir()
        make_dir(o2tuner_done_dir)

    @staticmethod
    def get_stages_done():
        """
        Get list of stages that have been done already
        """
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
        """
        Mark a stage as done
        """
        done_dir = get_done_dir()
        done_file = join(done_dir, f"DONE_{name}")
        with open(done_file, "w", encoding="utf-8") as done:
            done.write(rel_cwd)
