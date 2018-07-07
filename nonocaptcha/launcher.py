# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Launcher module. Mostly consists of Pyppetter patches."""

import asyncio
import atexit
import os
import psutil
import websockets
import shutil
import signal
import subprocess
import sys
import time

from pyppeteer import launcher
from pyppeteer import connection
from pyppeteer.browser import Browser
from pyppeteer.errors import NetworkError
from pyppeteer.util import check_chromium, chromium_excutable
from pyppeteer.util import download_chromium, merge_dict, get_free_port


DEFAULT_ARGS = [
    # ! = added in
    '--cryptauth-http-host ""',  # !
    "--disable-accelerated-2d-canvas", #!
    "--disable-affiliation-based-matching",  # !
    "--disable-answers-in-suggest",  # !
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-browser-side-navigation",
    "--disable-breakpad",  # !
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--disable-demo-mode",  # !
    "--disable-device-discovery-notifications",  # !
    "--disable-extensions",
    "--disable-hang-monitor",
    "--disable-java",  # !
    "--disable-popup-blocking",
    "--disable-preconnect",  # !
    "--disable-prompt-on-repost",
    "--disable-reading-from-canvas",  # !
    "--disable-sync",
    "--disable-translate",
    "--disable-web-security",  # !
    "--metrics-recording-only",
    "--no-first-run",
    "--no-sandbox",  # !
    "--safebrowsing-disable-auto-update",
]

AUTOMATION_ARGS = [
    "--enable-automation",
    "--password-store=basic",
    "--use-mock-keychain",
]


class Connection(connection.Connection):
    async def _recv_loop(self):
        async with self._ws as connection:
            self._connected = True
            self.connection = connection
            while self._connected:
                try:
                    resp = await self.connection.recv()
                    if resp:
                        self._on_message(resp)
                except asyncio.streams.IncompleteReadError:
                    break
                except websockets.ConnectionClosed:
                    break
                except ConnectionResetError:
                    break

    async def _async_send(self, msg: str):
        while not self._connected:
            await asyncio.sleep(self._delay)
        
        # Ignore errors on ungraceful exits
        try:
            await self.connection.send(msg)
        except asyncio.streams.IncompleteReadError:
            pass
        except websockets.ConnectionClosed:
            pass
        except ConnectionResetError:
            pass


class Launcher(launcher.Launcher):
    def __init__(self, options, **kwargs):
        """Make new launcher."""
        self.options = merge_dict(options, kwargs)
        self.port = get_free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.chrome_args = []
        self.proc = None

        if not self.options.get("ignoreDefaultArgs", False):
            self.chrome_args.extend(DEFAULT_ARGS)
            self.chrome_args.append(f"--remote-debugging-port={self.port}")

        self.chromeClosed = True
        if self.options.get("appMode", False):
            self.options["headless"] = False
        elif not self.options.get("ignoreDefaultArgs", False):
            self.chrome_args.extend(AUTOMATION_ARGS)

        self._tmp_user_data_dir = None
        self._parse_args()

        if self.options.get("devtools"):
            self.chrome_args.append("--auto-open-devtools-for-tabs")
            self.options["headless"] = False

        if "headless" not in self.options or self.options.get("headless"):
            self.chrome_args.extend(
                [
                    "--headless",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--mute-audio",
                ]
            )

        if "executablePath" in self.options:
            self.exec = self.options["executablePath"]
        else:
            if not check_chromium():
                download_chromium()
            self.exec = str(chromium_excutable())

        self.cmd = [self.exec] + self.chrome_args

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
                asyncio.wait(asyncio.ensure_future(self.killChrome()))

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

    def _cleanup_tmp_user_data_dir(self):
        def windows(path):
            cmd_path = os.path.join(
                os.environ["SYSTEMROOT"]
                if "SYSTEMROOT" in os.environ
                else r"C:\Windows",
                "System32",
                "cmd.exe",
            )
            args = [cmd_path, "/C", "rmdir", "/S", "/Q", path]
            subprocess.check_call(
                args, env={}, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )

        for retry in range(100):
            if self._tmp_user_data_dir and os.path.exists(
                self._tmp_user_data_dir
            ):
                if sys.platform == "win32":
                    windows(f"{self._tmp_user_data_dir}")
                else:
                    shutil.rmtree(self._tmp_user_data_dir, ignore_errors=True)
                if os.path.exists(self._tmp_user_data_dir):
                    time.sleep(0.01)
            else:
                break
        else:
            raise IOError('Unable to remove Temporary User Data')

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
                    self.proc.kill()
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
