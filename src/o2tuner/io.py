"""
Common I/O functionality
"""

import sys
from os.path import expanduser, isfile, isdir, exists
from os import makedirs
import json
import yaml

from o2tuner.log import get_logger

LOG = get_logger()


def exists_file(path):
    """
    Wrapper around python's os.path.isfile

    this has the possibility to add additional functionality if needed
    """
    return isfile(path)


def exists_dir(path):
    """
    Wrapper around python's os.path.isdir

    this has the possibility to add additional functionality if needed
    """
    return isdir(path)


def make_dir(path):
    """
    Create a directory
    """
    if exists(path):
        if exists_file(path):
            # if it exists and if that is actually a file instead of a directory, abort here...
            LOG.error("Attempted to create directory %s. However, a file seems to exist there, quitting", path)
            sys.exit(1)
            # ...otherwise just warn.
        LOG.debug("The directory %s already exists, not overwriting", path)
        return
    makedirs(path)


class NoAliasDumperYAML(yaml.SafeDumper):
    """
    Avoid refs in dumped YAML
    """
    def ignore_aliases(self, data):
        return True


def parse_yaml(path):
    """
    Wrap YAML reading
    """
    path = expanduser(path)
    try:
        with open(path, encoding="utf8") as in_file:
            return yaml.safe_load(in_file)
    except (OSError, IOError, yaml.YAMLError) as exc:
        LOG.error("ERROR: Cannot parse YAML from %s due to\n%s", path, exc)
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
        LOG.error("ERROR: Cannot write YAML to %s due to\n%s", path, eexc)
        sys.exit(1)


def parse_json(filepath):
    """
    Wrap JSON reading, needed for interfacing with O2 cut configuration files
    """
    filepath = expanduser(filepath)
    if not exists_file(filepath):
        LOG.error("ERROR: JSON file %s does not exist.", filepath)
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
