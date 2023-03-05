"""
Global configuration for pytest
"""

from os import makedirs
from os.path import exists, join
import shutil
import pytest

# Make sure all tests are executed in another working directory
# so we do not pollute the directory where the test is executed.


@pytest.fixture(autouse=True)
def test_workdir(request, monkeypatch):
    """
    Prepare a tests working directory and make sure it runs in there
    """
    work_dir = "o2tuner_pytest_workdir"
    if not exists(work_dir):
        makedirs(work_dir)

    this_function_name = request.function.__name__
    this_cwd = f"{request.fspath.basename}_{this_function_name}_dir"

    this_cwd = join(work_dir, this_cwd)

    if exists(this_cwd):
        shutil.rmtree(this_cwd)
    makedirs(this_cwd)
    monkeypatch.chdir(this_cwd)


@pytest.fixture
def needs_sqlite():
    """
    Mark as to-be-skipped if sqlite3 is not present
    """
    try:
        import sqlite3  # noqa: F401 pylint: disable=import-outside-toplevel,unused-import
    except ImportError:
        pytest.skip("no module sqlite3")
