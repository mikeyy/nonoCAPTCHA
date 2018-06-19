#!/usr/bin/env python3
# -*- coding: utf-8 -*-

version_info = (0, 0, 6)
__version__ = "{}.{}.{}".format(*version_info)


authors = (("Michael Mooney", "mikeyy@mikeyy.com"),)

authors_email = ", ".join("{}".format(email) for _, email in authors)

__license__ = "GPL-3.0"
__author__ = ", ".join(
    "{} <{}>".format(name, email) for name, email in authors
)

package_info = "An asynchronized Python library to automate solving ReCAPTCHA v2 by audio, using Microsoft Azure's Speech-to-Text API. "

# It's same persons right now
__maintainer__ = __author__

__all__ = (
    "__author__",
    "__author__",
    "__license__",
    "__maintainer__",
    "__version__",
    "version_info",
)

import os.path, sys
sys.path.append(os.getcwd())