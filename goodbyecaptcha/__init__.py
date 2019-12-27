#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import sys

version_info = (2, 3, 2)
__version__ = "{}.{}.{}".format(*version_info)

authors = (("MacKey-255", "mackeyfuturo@gmail.com"), ("Michael Mooney", "mikeyy@mikeyy.com"))

authors_email = ", ".join("{}".format(email) for _, email in authors)

__license__ = "GPL-3.0"
__author__ = ", ".join(
    "{} <{}>".format(name, email) for name, email in authors
)

package_info = (
    "An asynchronized Python library to automate solving ReCAPTCHA v2 by images/audio"
)
__maintainer__ = __author__

__all__ = (
    "__author__",
    "__author__",
    "__license__",
    "__maintainer__",
    "__version__",
    "version_info",
    "package_dir",
    "package_info",
)

sys.path.append(os.getcwd())
package_dir = os.path.dirname(os.path.abspath(__file__))
