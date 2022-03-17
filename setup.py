"""
Install this Python package.
"""


import re
import os.path
import site
import sys
from setuptools import setup, find_packages


class Setup():
    """
    Convenience wrapper (for C.I. purposes) of the `setup()` call form `setuptools`.
    """

    def __init__(self, **kw):
        self.conf = kw
        self.work_dir = os.path.abspath(os.path.dirname(__file__))

        # Automatically fill `package_data` from `MANIFEST.in`. No need to repeat lists twice
        assert "package_data" not in self.conf
        assert "include_package_data" not in self.conf
        package_data = {}
        with open(os.path.join(self.work_dir, "MANIFEST.in"), encoding="utf-8") as file_path:
            for line in file_path.readlines():
                line = line.strip()
                module_line = re.search(r"include\s+(.+)/([^/]+)", line)
                assert module_line
                module = module_line.group(1).replace("/", ".")
                file_name = module_line.group(2)
                if module not in package_data:
                    package_data[module] = []
                package_data[module].append(file_name)
        if package_data:
            self.conf["include_package_data"] = True
            self.conf["package_data"] = package_data

        # Automatically fill the long description from `README.md`. Filter out lines that look like
        # "badges".
        assert "long_description" not in self.conf
        assert "long_description_content_type" not in self.conf
        with open(os.path.join(self.work_dir, "README.md"), encoding="utf-8") as file_path:
            long_desc = "\n".join(
                [row for row in file_path if not row.startswith("[![")])
        self.conf["long_description"] = long_desc
        self.conf["long_description_content_type"] = "text/markdown"

    def __str__(self):
        return str(self.conf)

    def __call__(self):
        setup(**self.conf)


SETUP = Setup(
    name="o2tuner",

    # LAST-TAG is a placeholder. Automatically replaced at deploy time with the right tag
    version="0.0.1",

    description="Minimal heavy ion physics environment for Machine Learning",

    url="https://github.com/mconcas/o2tuner",
    author="mconcas",
    author_email="mconcas@cern.ch",
    license="GPL",

    # See https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9"
    ],

    # What does your project relate to?
    keywords="",

    # You can just specify the packages manually here if your project is simple. Or you can use
    # find_packages().
    packages=find_packages(exclude=['tutorials']),

    # List run-time dependencies here. These will be installed by pip when your project is
    # installed. For an analysis of "install_requires" vs pip's requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=["optuna", "colorama", "click"],

    python_requires=">=3.8",

    # List additional groups of dependencies here (e.g. development dependencies). You can install
    # these using the following syntax, for example:
    # $ pip install -e .[dev,test]
    extras_require={
        "dev": []
    },

    # Although 'package_data' is the preferred approach, in some case you may need to place data
    # files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files
    data_files=[],

    # To provide executable scripts, use entry points in preference to the "scripts" keyword. Entry
    # points provide cross-platform support and allow pip to create the appropriate form of
    # executable for the target platform. See:
    # https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
    entry_points={
        "console_scripts": ["o2tuner = o2tuner:entrypoint"]
    }
)

if __name__ == "__main__":
    site.ENABLE_USER_SITE = "--user" in sys.argv[1:]
    SETUP()
