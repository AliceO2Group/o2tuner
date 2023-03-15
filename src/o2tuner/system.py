"""
Common system tools
"""
import sys
from os.path import join, abspath
import importlib
import signal
import psutil

from o2tuner.log import get_logger
from o2tuner.exception import O2TunerStopOptimisation
from o2tuner.bookkeeping import add_system_attr, get_system_attr

LOG = get_logger()

LOADED_MODULES = {}


def run_command(cmd, *, cwd="./", log_file=None, wait=True):
    """
    Prepare command and run
    """
    if log_file is None:
        log_file = "log.log"
    cmd = f"{cmd} >{log_file} 2>&1"
    LOG.info("Running command %s", cmd)
    proc = psutil.Popen(["/bin/bash", "-c", cmd], cwd=cwd)
    if wait:
        proc.wait()
        if ret := proc.returncode:
            # check the return code and exit if != 0, if the user does not want to wait, they are responsible to handle potential errors
            LOG.error("There seems to have been a problem with the launched process, its exit code was %d.", ret)
            sys.exit(ret)
    return proc, join(cwd, log_file)


def load_file_as_module(path, module_name):
    """
    Load a given file as a module
    """
    lookup_key = abspath(path)
    if path in LOADED_MODULES:
        return LOADED_MODULES[lookup_key].__name__

    if module_name in sys.modules:
        LOG.error("Module name %s already present, cannot load", module_name)
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    LOADED_MODULES[lookup_key] = module
    return module.__name__


def import_function_from_module(module_name, function_name):
    """
    Wrapper to manually load a function from a module
    """
    module = importlib.import_module(module_name)
    if not hasattr(module, function_name):
        LOG.error("Cannot find function %s in module %s", function_name, module.__name__)
        sys.exit(1)
    return getattr(module, function_name)


def import_function_from_file(path, function_name):
    """
    Manually load a function from a file
    """
    path = abspath(path)
    module_name = load_file_as_module(path, path.replace("/", "_").replace(".", "_"))
    return import_function_from_module(module_name, function_name)


def terminate(procs):
    """
    Terminate a bunch of processes (or at least try to)
    """
    for proc in procs:
        LOG.info("Terminating %s", proc)
        try:
            proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def kill(procs):
    """
    Kill a bunch of processes (or at least try to)
    """
    _, alive = psutil.wait_procs(procs, timeout=3)
    for proc in alive:
        LOG.info("Killing %s", proc)
        try:
            proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


def kill_recursive(process, timeout=None):
    """
    Kill a process recursively (with all its children)
    """
    if not isinstance(process, psutil.Process):
        # assume it comes from multiprocessing
        process = psutil.Process(process.pid)
    procs = []
    if timeout:
        try:
            process.wait(timeout)
        except psutil.TimeoutExpired:
            pass

    try:
        procs = process.children(recursive=True)
    except psutil.NoSuchProcess:
        pass

    terminate(procs)
    kill(procs)


class O2TunerSignalHandler:
    """
    Central class for signal handling
    """
    def __init__(self):
        self.cached_signal_optimisation = False
        self.running_optimisation = False
        signal.signal(signal.SIGQUIT, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.siginterrupt(signal.SIGQUIT, False)
        signal.siginterrupt(signal.SIGINT, False)

    def set_optimisation(self, flag=True):
        """
        Set this when in optimisation stage
        """
        self.cached_signal_optimisation = False
        self.running_optimisation = flag

    def signal_handler(self, signum, _frame):
        """
        Signal handling implementation
        """
        # basically forcing shut down of all child processes
        LOG.info("Signal %d caught", signum)
        if signum == signal.SIGINT:
            kill_recursive(psutil.Process())
            sys.exit(1)
        elif signum == signal.SIGQUIT:
            raise O2TunerStopOptimisation("Stop optimisation")


def get_signal_handler():
    """
    Get the central signal handler
    """
    name = "O2TunerSignalHandler"
    signal_handler = get_system_attr(name, None)

    if signal_handler:
        return signal_handler

    handler = O2TunerSignalHandler()
    add_system_attr(name, handler)
    return handler
