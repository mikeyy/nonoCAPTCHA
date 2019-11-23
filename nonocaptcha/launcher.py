# !/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Launcher module. Workarounds to launch browsers asynchronously. """

from pyppeteer import launcher


class Launcher(launcher.Launcher):
    # TODO: remove this class, this used to have hacks to run the browser
    #       asynchronously which are now merged into pyppeteer_fork
    pass
