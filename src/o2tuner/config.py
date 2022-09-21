"""
Configuration functionality and parsing
"""
import dataclasses
from os.path import join, basename, abspath
from glob import glob

from o2tuner.io import make_dir, parse_yaml, exists_dir


@dataclasses.dataclass
class WorkDir:
    """
    Use this object to set the working directory globally
    """
    path = None


WORK_DIR = WorkDir()


def get_work_dir():
    return WORK_DIR.path


def set_work_dir(work_dir):
    WORK_DIR.path = abspath(work_dir)


def resolve_path(rel_cwd):
    return join(WORK_DIR.path, rel_cwd)


def load_config(config_path):
    return parse_yaml(config_path)


def get_done_dir():
    return join(WORK_DIR.path, "o2tuner_done")


def prepare_work_dir():
    make_dir(WORK_DIR.path)
    o2tuner_done_dir = get_done_dir()
    make_dir(o2tuner_done_dir)


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


def set_stage_done(name, rel_cwd):
    done_dir = get_done_dir()
    done_file = join(done_dir, f"DONE_{name}")
    with open(done_file, "w", encoding="utf-8") as done:
        done.write(rel_cwd)
