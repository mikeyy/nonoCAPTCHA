# !/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Launcher module. Workarounds to launch browsers asynchronously. """

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time

from copy import copy
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

from pyppeteer import __pyppeteer_home__
from pyppeteer import launcher
from pyppeteer.browser import Browser
from pyppeteer.connection import Connection
from pyppeteer.chromium_downloader import current_platform
from pyppeteer.errors import BrowserError
from pyppeteer.helper import addEventListener, removeEventListeners
from pyppeteer.util import check_chromium, chromium_executable
from pyppeteer.util import download_chromium, merge_dict, get_free_port

pyppeteer_home = Path(__pyppeteer_home__)
CHROME_PROFILE_PATH = pyppeteer_home / '.dev_profile'

DEFAULT_ARGS = [
    '--disable-background-networking', '--disable-background-timer-throttling',
    '--disable-breakpad', '--disable-browser-side-navigation',
    '--disable-client-side-phishing-detection', '--disable-default-apps',
    '--disable-dev-shm-usage', '--disable-extensions',
    '--disable-features=site-per-process', '--disable-hang-monitor',
    '--disable-popup-blocking', '--disable-prompt-on-repost', '--disable-sync',
    '--disable-translate', '--metrics-recording-only', '--no-first-run',
    '--safebrowsing-disable-auto-update', '--enable-automation',
    '--password-store=basic', '--use-mock-keychain'
]


class Launcher(launcher.Launcher):
    """Chrome parocess launcher class."""

    def __init__(
            self,
            options,  # noqa: C901
            **kwargs) -> None:
        """Make new launcher."""
        options = merge_dict(options, kwargs)

        self.port = get_free_port()
        self.url = f'http://127.0.0.1:{self.port}'
        self._loop = options.get('loop', asyncio.get_event_loop())
        self.chromeClosed = True

        ignoreDefaultArgs = options.get('ignoreDefaultArgs', False)
        args = options.get('args', list())
        self.dumpio = options.get('dumpio', False)
        executablePath = options.get('executablePath')
        self.env = options.get('env')
        self.handleSIGINT = options.get('handleSIGINT', True)
        self.handleSIGTERM = options.get('handleSIGTERM', True)
        self.handleSIGHUP = options.get('handleSIGHUP', True)
        self.ignoreHTTPSErrors = options.get('ignoreHTTPSErrors', False)
        self.defaultViewport = options.get('defaultViewport', {
            'width': 800,
            'height': 600
        })  # noqa: E501
        self.slowMo = options.get('slowMo', 0)
        self.timeout = options.get('timeout', 30000)
        self.autoClose = options.get('autoClose', True)

        logLevel = options.get('logLevel')
        if logLevel:
            logging.getLogger('pyppeteer').setLevel(logLevel)

        self.chromeArguments = list()
        if not ignoreDefaultArgs:
            self.chromeArguments.extend(defaultArgs(options))
        elif isinstance(ignoreDefaultArgs, list):
            self.chromeArguments.extend(
                filter(
                    lambda arg: arg not in ignoreDefaultArgs,
                    defaultArgs(options),
                ))
        else:
            self.chromeArguments.extend(args)

        self.temporaryUserDataDir = None

        if not any(
                arg for arg in self.chromeArguments
                if arg.startswith('--remote-debugging-')):
            self.chromeArguments.append(f'--remote-debugging-port={self.port}')

        if not any(
                arg for arg in self.chromeArguments
                if arg.startswith('--user-data-dir')):
            if not CHROME_PROFILE_PATH.exists():
                CHROME_PROFILE_PATH.mkdir(parents=True)
            self.temporaryUserDataDir = tempfile.mkdtemp(
                dir=str(CHROME_PROFILE_PATH))  # noqa: E501
            self.chromeArguments.append(
                f'--user-data-dir={self.temporaryUserDataDir}')  # noqa: E501

        self.chromeExecutable = executablePath
        if not self.chromeExecutable:
            if not check_chromium():
                download_chromium()
            self.chromeExecutable = str(chromium_executable())

        self.cmd = [self.chromeExecutable] + self.chromeArguments

    async def launch(self):
        self.chromeClosed = False
        self.connection = None

        options = dict()
        options['env'] = self.env
        if not self.dumpio:
            options['stdout'] = asyncio.subprocess.PIPE
            options['stderr'] = asyncio.subprocess.STDOUT

        self.proc = await asyncio.subprocess.create_subprocess_exec(
            *self.cmd,
            **options)
        # Signal handlers for exits used to be here
        connectionDelay = self.slowMo
        self.browserWSEndpoint = await self._get_ws_endpoint()
        self.connection = Connection(self.browserWSEndpoint, self._loop,
                                     connectionDelay)

        browser = await Browser.create(
            self.connection, [], self.ignoreHTTPSErrors, self.defaultViewport,
            self.proc, self.killChrome)
        await self.ensureInitialPage(browser)
        return browser

    async def _get_ws_endpoint(self) -> str:
        url = self.url + '/json/version'
        while self.proc.returncode is None and not self.chromeClosed:
            await asyncio.sleep(0.1)
            try:
                with urlopen(url) as f:
                    data = json.loads(f.read().decode())
                break
            except URLError:
                continue
        else:
            raise BrowserError('Browser closed unexpectedly:\n{}'.format(
                await self.proc.stdout.read().decode()))
        return data['webSocketDebuggerUrl']

    async def ensureInitialPage(self, browser):
        """Wait for initial page target to be created."""
        for target in browser.targets():
            if target.type == 'page':
                return

        initialPagePromise = self._loop.create_future()

        def initialPageCallback():
            initialPagePromise.set_result(True)

        def check_target(target):
            if target.type == 'page':
                initialPageCallback()

        listeners = [addEventListener(browser, 'targetcreated', check_target)]
        await initialPagePromise
        removeEventListeners(listeners)

    async def waitForChromeToClose(self):
        if self.proc.returncode is None and not self.chromeClosed:
            self.chromeClosed = True
            try:
                self.proc.terminate()
                await self.proc.wait()
            except (OSError, ProcessLookupError):
                pass

    async def killChrome(self):
        """Terminate chromium process."""
        if self.connection and self.connection._connected:
            try:
                await self.connection.send("Browser.close")
                await self.connection.dispose()
            except Exception:
                pass
        if self.temporaryUserDataDir and os.path.exists(self.temporaryUserDataDir):
            # Force kill chrome only when using temporary userDataDir
            await self.waitForChromeToClose()
            self._cleanup_tmp_user_data_dir()

    def _cleanup_tmp_user_data_dir(self):
        for retry in range(100):
            if self.temporaryUserDataDir and os.path.exists(
                    self.temporaryUserDataDir):
                shutil.rmtree(self.temporaryUserDataDir, ignore_errors=True)
                if os.path.exists(self.temporaryUserDataDir):
                    time.sleep(0.01)
            else:
                break
        else:
            raise IOError('Unable to remove Temporary User Data')


def defaultArgs(options={}, **kwargs):  # noqa: C901,E501
    """Get the default flags the chromium will be launched with.

    ``options`` or keyword arguments are set of configurable options to set on
    the browser. Can have the following fields:

    * ``headless`` (bool): Whether to run browser in headless mode. Defaults to
      ``True`` unless the ``devtools`` option is ``True``.
    * ``args`` (List[str]): Additional arguments to pass to the browser
      instance. The list of chromium flags can be found
      `here <http://peter.sh/experiments/chromium-command-line-switches/>`__.
    * ``userDataDir`` (str): Path to a User Data Directory.
    * ``devtools`` (bool): Whether to auto-open DevTools panel for each tab. If
      this option is ``True``, the ``headless`` option will be set ``False``.
    """
    options = merge_dict(options, kwargs)
    devtools = options.get('devtools', False)
    headless = options.get('headless', not devtools)
    args = options.get('args', list())
    userDataDir = options.get('userDataDir')
    chromeArguments = copy(DEFAULT_ARGS)

    if userDataDir:
        chromeArguments.append(f'--user-data-dir={userDataDir}')
    if devtools:
        chromeArguments.append('--auto-open-devtools-for-tabs')
    if headless:
        chromeArguments.extend((
            '--headless',
            '--hide-scrollbars',
            '--mute-audio',
        ))
        if current_platform().startswith('win'):
            chromeArguments.append('--disable-gpu')

    if all(map(lambda arg: arg.startswith('-'), args)):  # type: ignore
        chromeArguments.append('about:blank')
    chromeArguments.extend(args)

    return chromeArguments
