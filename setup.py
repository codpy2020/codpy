﻿# Copyright (C)

import os
from distutils.core import setup

from setuptools import find_packages, setup

__version__ = "0.1.11"

DISTNAME = "codpy"
DESCRIPTION = "An RKHS based module for numerics, statistic and machine learning"
MAINTAINER = "jean-marc mercier"
MAINTAINER_EMAIL = "jeanmarc.mercier@gmail.com"
URL = "https://github.com/johnlem/codpy_alpha"
# DOWNLOAD_URL = 'https://github.com/johnlem/codpy_alpha'
LICENSE = "new BSD"
PROJECT_URLS = {
    "Bug Tracker": "https://github.com/johnlem/codpy_alpha/issues",
    "Documentation": "https://",
    "Source Code": "https://github.com/johnlem/codpy_alpha",
}

codpy_path = os.path.dirname(__file__)
codpy_path = os.path.join(codpy_path, "codpy")


def package_files(directory):
    paths = []
    for path, directories, filenames in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join("..", path, filename))
    return paths


extra_files = package_files(codpy_path)
long_description = open("README.md", "r").read()

# print("find_packages():",find_packages(),)

setup(
    name=DISTNAME,
    version=__version__,
    author=MAINTAINER,
    maintainer=MAINTAINER,
    author_email=MAINTAINER_EMAIL,
    description=DESCRIPTION,
    license=LICENSE,
    url=URL,
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    package_data={"": extra_files},
    classifiers=[
        # trove classifiers
        # the full list is here: https://pypi.python.org/pypi?%3aaction=list_classifiers
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Win32 (MS Windows)",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
        "Operating System :: Microsoft :: Windows :: Windows 11",
    ],
    install_requires=[
        "codpydll==0.1.4",
        "pandas==1.5.0",
        "mkl",
        "scikit-learn",
        "scipy",
        "numpy==1.24.3",
        "xarray==2022.9.0",
        "matplotlib",
        "statsmodels"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    #  extras_require={
    #  'win32': 'pywin32'
    # }
)
