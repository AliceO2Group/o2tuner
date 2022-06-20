"""
Common system tools
"""

from os.path import join
import psutil


def run_command(cmd, cwd, *, log_file=None, wait=False):
    """
    Prepare command and run
    """
    if log_file is None:
        log_file = "log.log"
    cmd = f"{cmd}>{log_file} 2>&1"
    print(f"Running command {cmd}")
    proc = psutil.Popen(["/bin/bash", "-c", cmd], cwd=cwd)
    if wait:
        proc.wait()
    return proc, join(cwd, log_file)
