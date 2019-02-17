# !/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Launcher module. Workarounds to launch browsers asynchronously. """

import asyncio
import json
import logging
import os

from urllib.request import urlopen
from urllib.error import URLError

from pyppeteer import launcher
from pyppeteer.browser import Browser
from pyppeteer.connection import Connection
from pyppeteer.errors import BrowserError
from pyppeteer.util import check_chromium, chromium_executable
from pyppeteer.util import download_chromium, merge_dict, get_free_port


class Launcher(launcher.Launcher):
    """Chrome parocess launcher class."""

    def __init__(self, options,  # noqa: C901
                 **kwargs) -> None:
        """Make new launcher."""
        self.options = merge_dict(options, kwargs)
        self.port = get_free_port()
        self.url = f'http://127.0.0.1:{self.port}'
        self.chrome_args = [f'--remote-debugging-port={self.port}']
        self._loop = self.options.get('loop', asyncio.get_event_loop())

        logLevel = self.options.get('logLevel')
        if logLevel:
            logging.getLogger('pyppeteer').setLevel(logLevel)
        self.chromeClosed = True
        if self.options.get('appMode', False):
            self.options['headless'] = False
        self._tmp_user_data_dir = None
        self._parse_args()
        if self.options.get('devtools'):
            self.chrome_args.append('--auto-open-devtools-for-tabs')
            self.options['headless'] = False
        if 'headless' not in self.options or self.options.get('headless'):
            self.chrome_args.extend([
                '--headless',
                '--disable-gpu',
                '--hide-scrollbars',
                '--mute-audio',
            ])
        if 'executablePath' in self.options:
            self.exec = self.options['executablePath']
        else:
            if not check_chromium():
                download_chromium()
            self.exec = str(chromium_executable())
        self.cmd = [self.exec] + self.chrome_args

    async def launch(self):
        self.chromeClosed = False
        self.connection = None
        env = self.options.get("env")
        self.proc = await asyncio.subprocess.create_subprocess_exec(
            *self.cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        # Signal handlers for exits used to be here
        connectionDelay = self.options.get("slowMo", 0)
        self.browserWSEndpoint = await self._get_ws_endpoint()
        self.connection = Connection(
            self.browserWSEndpoint, self._loop, connectionDelay)
        return await Browser.create(
            self.connection, self.options, self.proc, self.killChrome)

    async def _get_ws_endpoint(self) -> str:
        url = self.url + '/json/version'
        while self.proc.returncode is None:
            await asyncio.sleep(0.1)
            try:
                with urlopen(url) as f:
                    data = json.loads(f.read().decode())
                break
            except URLError:
                continue
        else:
            raise BrowserError(
                'Browser closed unexpectedly:\n{}'.format(
                    await self.proc.stdout.read().decode()
                )
            )
        return data['webSocketDebuggerUrl']

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
        if self._tmp_user_data_dir and os.path.exists(self._tmp_user_data_dir):
            # Force kill chrome only when using temporary userDataDir
            await self.waitForChromeToClose()
            self._cleanup_tmp_user_data_dir()
