#!/usr/bin/env python3
# -*- coding=utf-8 -*-

"""
flaskmongorm
--------------

simple wrapper for flask-pymongo
"""

from pathlib import Path

from setuptools import setup

version = ""
p = Path(__file__) / "../flaskmongorm/__init__.py"
with p.resolve().open(encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__ = "):
            version = line.split("=")[-1].strip().replace("'", "")
            break

setup(
    name="flaskmongorm",
    version=version.replace('"', ""),
    url="https://github.com/lixxu/flaskmongorm",
    license="BSD-3-Clause",
    author="Lix Xu",
    author_email="xuzenglin@gmail.com",
    description="Simple wrapper for flask-pymongo",
    long_description=__doc__,
    packages=["flaskmongorm"],
    zip_safe=False,
    platforms="any",
    install_requires=[
        "flask-pymongo",
        "pymongo>=3.6, <4.0",
        "tzdata",
        'backports.zoneinfo;python_version<"3.9"',
    ],
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
