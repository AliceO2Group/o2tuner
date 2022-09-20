"""
Common I/O functionality
"""

import sys
from os.path import expanduser, isfile, isdir, exists, abspath, join
from os import makedirs, remove, listdir
from shutil import rmtree
import json
import yaml

from o2tuner.log import Log

LOG = Log()


def exists_file(path):
    """wrapper around python's os.path.isfile

    this has the possibility to add additional functionality if needed
    """
    return isfile(path)


def exists_dir(path):
    """wrapper around python's os.path.isdir

    this has the possibility to add additional functionality if needed
    """
    return isdir(path)


def make_dir(path):
    """create a directory
    """
    if exists(path):
        if exists_file(path):
            # if it exists and if that is actually a file instead of a directory, fail here...
            LOG.error(f"Attempted to create directory {path}. However, a file seems to exist there, quitting")
            sys.exit(1)
            # ...otherwise just warn.
        LOG.warning(f"The directory {path} already exists, not overwriting")
        return
    # make the whole path structure
    makedirs(path)


def remove_any_impl(to_be_removed, keep=None):

    if not exists(to_be_removed):
        return

    if isfile(to_be_removed):
        remove(to_be_removed)
        return

    if not keep:
        rmtree(to_be_removed)
        return

    # at this point we are sure that it is a directory and that certain things should be kept
    contains = [join(to_be_removed, ld) for ld in listdir(to_be_removed)]

    # figure out potential overlap between this path and things to be kept
    keep_this = []
    for con in contains:
        for k in keep:
            if not k.find(con):
                # means found at index 0
                keep_this.append(con)

    to_be_removed = [con for con in contains if con not in keep_this]

    for tbr in to_be_removed:
        remove_any_impl(tbr, keep_this)


def remove_dir(to_be_removed, keep=None):
    """
    remove a file or directory but keep certain things inside on request
    """
    to_be_removed = abspath(to_be_removed)
    if keep:
        keep = [join(to_be_removed, k) for k in keep]
    remove_any_impl(to_be_removed, keep)


########
# YAML #
########
class NoAliasDumperYAML(yaml.SafeDumper):
    """
    Avoid refs in dumped YAML
    """
    def ignore_aliases(self, data):
        return True


def parse_yaml(path):
    """
    Wrap YAML reading
    https://stackoverflow.com/questions/13518819/avoid-references-in-pyyaml
    """
    path = expanduser(path)
    try:
        with open(path, encoding="utf8") as in_file:
            return yaml.safe_load(in_file)
    except (OSError, IOError, yaml.YAMLError) as exc:
        LOG.error(f"ERROR: Cannot parse YAML from {path} due to\n{exc}")
        sys.exit(1)


def dump_yaml(to_yaml, path, *, no_refs=False):
    """
    Wrap YAML writing
    """
    path = expanduser(path)
    try:
        with open(path, 'w', encoding="utf8") as out_file:
            if no_refs:
                yaml.dump_all([to_yaml], out_file, Dumper=NoAliasDumperYAML)
            else:
                yaml.safe_dump(to_yaml, out_file)
    except (OSError, IOError, yaml.YAMLError) as eexc:
        LOG.error(f"ERROR: Cannot write YAML to {path} due to\n{eexc}")
        sys.exit(1)


########
# YAML #
########
def parse_json(filepath):
    """
    Wrap JSON reading, needed for interfacing with O2 cut configuration files
    """
    filepath = expanduser(filepath)
    if not exists_file(filepath):
        LOG.error(f"ERROR: JSON file {filepath} does not exist.")
        sys.exit(1)
    with open(filepath, "r", encoding="utf8") as config_file:
        return json.load(config_file)


def dump_json(to_json, path):
    """
    Wrap JSON writing, needed for interfacing with O2 cut configuration files
    """
    path = expanduser(path)
    with open(path, 'w', encoding="utf8") as config_file:
        json.dump(to_json, config_file, indent=2)
