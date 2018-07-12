# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Launcher module. Mostly consists of Pyppetter patches."""

import asyncio
import atexit
import os
import psutil
import signal
import sys
import websockets

from pyppeteer import launcher
from pyppeteer.browser import Browser
from pyppeteer.connection import Connection
from pyppeteer.errors import NetworkError
from pyppeteer.util import check_chromium, chromium_excutable
from pyppeteer.util import download_chromium, merge_dict, get_free_port


DEFAULT_ARGS = [
    '--cryptauth-http-host ""'
    '--disable-accelerated-2d-canvas',
    '--disable-background-networking',
    '--disable-background-timer-throttling',
    '--disable-browser-side-navigation',
    '--disable-client-side-phishing-detection',
    '--disable-default-apps',
    '--disable-dev-shm-usage',
    '--disable-device-discovery-notifications',
    '--disable-extensions',
    '--disable-features=site-per-process',
    '--disable-hang-monitor',
    '--disable-java',
    '--disable-popup-blocking',
    '--disable-prompt-on-repost',
    '--disable-reading-from-canvas',
    '--disable-sync',
    '--disable-translate',
    '--disable-web-security',
    '--metrics-recording-only',
    '--no-first-run',
    '--no-sandbox',
    '--noerrdialogs',
    '--safebrowsing-disable-auto-update',
]

AUTOMATION_ARGS = [
    "--enable-automation",
    "--password-store=basic",
    "--use-mock-keychain",
]


class Launcher(launcher.Launcher):
    async def launch(self):
        env = self.options.get("env")
        self.proc = await asyncio.subprocess.create_subprocess_exec(
            *self.cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        self.chromeClosed = False
        self.connection = None

        def _close_process(*args, **kwargs):
            if not self.chromeClosed:
                asyncio.get_event_loop().run_until_complete(self.killChrome())

        # dont forget to close browser process
        atexit.register(_close_process)
        if self.options.get("handleSIGINT", True):
            signal.signal(signal.SIGINT, _close_process)
        if self.options.get("handleSIGTERM", True):
            signal.signal(signal.SIGTERM, _close_process)
        if not sys.platform.startswith("win"):
            # SIGHUP is not defined on windows
            if self.options.get("handleSIGHUP", True):
                signal.signal(signal.SIGHUP, _close_process)

        connectionDelay = self.options.get("slowMo", 0.1)
        self.browserWSEndpoint = self._get_ws_endpoint()
        self.connection = Connection(self.browserWSEndpoint, connectionDelay)
        return await Browser.create(
            self.connection, self.options, self.proc, self.killChrome
        )

    async def waitForChromeToClose(self):
        if self.proc:
            if self.proc.returncode is None and not self.chromeClosed:
                self.chromeClosed = True
                if psutil.pid_exists(self.proc.pid):
                    process = psutil.Process(self.proc.pid)
                    for proc in process.children(recursive=True):
                        try:
                            proc.kill()
                        except psutil._exceptions.NoSuchProcess:
                            pass
                    self.proc.terminate()
                    await self.proc.wait()

    async def killChrome(self):
        """Terminate chromium process."""
        if self.connection and self.connection._connected:
            try:
                await self.connection.send("Browser.close")
                await self.connection.dispose()
            except asyncio.streams.IncompleteReadError:
                pass
            except websockets.exceptions.ConnectionClosed:
                pass
            except ConnectionResetError:
                pass
            except NetworkError:
                pass

        if self._tmp_user_data_dir and os.path.exists(self._tmp_user_data_dir):
            # Force kill chrome only when using temporary userDataDir
            await self.waitForChromeToClose()
            self._cleanup_tmp_user_data_dir()
