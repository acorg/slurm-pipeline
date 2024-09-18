#!/usr/bin/env python

from setuptools import setup


# Modified from http://stackoverflow.com/questions/2058802/
# how-can-i-get-the-version-defined-in-setup-py-setuptools-in-my-package
def version():
    import os
    import re

    init = os.path.join("slurm_pipeline", "__init__.py")
    with open(init) as fp:
        initData = fp.read()
    match = re.search(r"^__version__ = ['\"]([^'\"]+)['\"]", initData, re.M)
    if match:
        return match.group(1)
    else:
        raise RuntimeError("Unable to find version string in %r." % init)


setup(
    name="slurm-pipeline",
    version=version(),
    packages=["slurm_pipeline"],
    include_package_data=True,
    url="https://github.com/acorg/slurm-pipeline",
    download_url="https://github.com/acorg/slurm-pipeline",
    author="Terry Jones",
    author_email="terry@jon.es",
    keywords=["slurm", "sbatch"],
    scripts=[
        "bin/remove-repeated-headers.py",
        "bin/sbatch.py",
        "bin/slurm-pipeline.py",
        "bin/slurm-pipeline-status.py",
        "bin/slurm-pipeline-status-plot.py",
        "bin/slurm-pipeline-version.py",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    install_requires=[
        "pandas",
        "plotly",
        "pytest>=6.2.2",
    ],
    extras_require={
        "dev": [
            "flake8",
            "pandas",
            "pycodestyle",
            "pytest",
        ],
        "test": [
            "pandas",
            "pytest",
        ],
    },
    license="MIT",
    description="A Python class and utility script for scheduling SLURM jobs.",
)
