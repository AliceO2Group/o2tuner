"""
Common system tools
"""
import sys
from os.path import join, abspath
import importlib
import psutil

from o2tuner.log import Log

LOG = Log()

LOADED_MODULES = {}


def run_command(cmd, *, cwd="./", log_file=None, wait=True):
    """
    Prepare command and run
    """
    if log_file is None:
        log_file = "log.log"
    cmd = f"{cmd} >{log_file} 2>&1"
    LOG.info(f"Running command {cmd}")
    proc = psutil.Popen(["/bin/bash", "-c", cmd], cwd=cwd)
    if wait:
        proc.wait()
    return proc, join(cwd, log_file)


def load_file_as_module(path, module_name):
    """
    load path as module
    """
    lookup_key = abspath(path)
    if path in LOADED_MODULES:
        return LOADED_MODULES[lookup_key].__name__

    if module_name in sys.modules:
        LOG.error(f"Module name {module_name} already present, cannot load")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    LOADED_MODULES[lookup_key] = module
    return module.__name__


def import_function_from_module(module_name, function_name):
    module = importlib.import_module(module_name)
    if not hasattr(module, function_name):
        LOG.error(f"Cannot find function {function_name} in module {module.__name__}")
        sys.exit(1)
    return getattr(module, function_name)


def import_function_from_file(path, function_name):
    module_name = load_file_as_module(path, path.replace("/", "_").replace(".", "_"))
    return import_function_from_module(module_name, function_name)
