#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path, sys

version_info = (0, 0, 14)
__version__ = "{}.{}.{}".format(*version_info)


authors = (("Michael Mooney", "mikeyy@mikeyy.com"),)

authors_email = ", ".join("{}".format(email) for _, email in authors)

__license__ = "GPL-3.0"
__author__ = ", ".join(
    "{} <{}>".format(name, email) for name, email in authors
)

package_info = "An asynchronized Python library to automate solving ReCAPTCHA v2 by audio, using Microsoft Azure's Speech-to-Text API. "

__package_dir__ = os.path.dirname(os.path.abspath(__file__))

__maintainer__ = __author__

__all__ = (
    "__author__",
    "__author__",
    "__license__",
    "__maintainer__",
    "__package_dir__",
    "__version__",
    "version_info",
)

sys.path.append(os.getcwd())
