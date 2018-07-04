#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys

version_info = (1, 5, 8)
__version__ = "{}.{}.{}".format(*version_info)


authors = (("Michael Mooney", "mikeyy@mikeyy.com"),)

authors_email = ", ".join("{}".format(email) for _, email in authors)

__license__ = "GPL-3.0"
__author__ = ", ".join(
    "{} <{}>".format(name, email) for name, email in authors
)

package_info = (
    "An asynchronized Python library to automate solving ReCAPTCHA v2 by audio"
)
__maintainer__ = __author__

__all__ = (
    "__author__",
    "__author__",
    "__license__",
    "__maintainer__",
    "__version__",
    "version_info",
)

sys.path.append(os.getcwd())

try:
    import yaml
    with open("config.yml", 'r') as f:
        settings = yaml.load(f)
        package_dir = os.path.dirname(os.path.abspath(__file__))
except FileNotFoundError:
    print(
        "Solver can't run without a configuration file!\n"
        "An example (config.example.yaml) has been copied to your current "
        "folder."
    )

    import sys
    from shutil import copyfile

    copyfile(f"{__package_dir__}/config.example.yaml", "config.example.yaml")
    sys.exit(0)
