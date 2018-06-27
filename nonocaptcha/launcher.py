import asyncio
import atexit
import psutil
import os
import signal
import sys

from pyppeteer import launcher
from pyppeteer import connection
from pyppeteer.browser import Browser
from pyppeteer.connection import Connection
from pyppeteer.util import check_chromium, chromium_excutable
from pyppeteer.util import download_chromium, merge_dict, get_free_port


DEFAULT_ARGS = [
    #! = added in
    '--cryptauth-http-host ""', #!
    '--disable-affiliation-based-matching', #!
    '--disable-answers-in-suggest', #!
    '--disable-background-networking', 
    '--disable-background-timer-throttling',
    '--disable-browser-side-navigation',
    '--disable-breakpad', #!
    '--disable-client-side-phishing-detection',
    '--disable-default-apps',
    '--disable-demo-mode', #!
    '--disable-device-discovery-notifications', #!
    '--disable-extensions',
    '--disable-hang-monitor',
    '--disable-java', #!
    '--disable-popup-blocking',
    '--disable-preconnect', #!
    '--disable-prompt-on-repost',
    '--disable-reading-from-canvas',#!
    '--disable-sync',
    '--disable-translate',
    '--disable-web-security', #!
    '--metrics-recording-only',
    '--no-first-run',
    '--no-sandbox', #!
    '--safebrowsing-disable-auto-update',
]

AUTOMATION_ARGS = [
    '--enable-automation',
    '--password-store=basic',
    '--use-mock-keychain',
]




class Connection(connection.Connection):
    async def _async_send(self, msg):
        while not self._connected:
            await asyncio.sleep(self._delay)

        try:
            await self.connection.send(msg)
        except:
            pass




class Launcher(launcher.Launcher):
    def __init__(self, options, **kwargs):
        """Make new launcher."""
        self.options = merge_dict(options, kwargs)
        self.port = get_free_port()
        self.url = f'http://127.0.0.1:{self.port}'
        self.chrome_args = []

        if not self.options.get('ignoreDefaultArgs', False):
            self.chrome_args.extend(DEFAULT_ARGS)
            self.chrome_args.append(
                f'--remote-debugging-port={self.port}',
            )

        self.chromeClosed = True
        if self.options.get('appMode', False):
            self.options['headless'] = False
        elif not self.options.get('ignoreDefaultArgs', False):
            self.chrome_args.extend(AUTOMATION_ARGS)

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
            self.exec = str(chromium_excutable())

        self.cmd = [self.exec] + self.chrome_args
        
    async def _proc(self):
        env = self.options.get("env")
        self.proc = await asyncio.subprocess.create_subprocess_exec(
            *self.cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=env
        )
        return self.proc

    async def launch(self, proc):
        self.proc = proc
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

        connectionDelay = self.options.get("slowMo", 0)
        self.browserWSEndpoint = self._get_ws_endpoint()
        self.connection = Connection(self.browserWSEndpoint, connectionDelay)
        return await Browser.create(
            self.connection, self.options, self.proc, self.killChrome
        )
                
    def waitForChromeToClose(self) -> None:
        pass

    async def killChrome(self) -> None:
        """Terminate chromium process."""
        if self.connection and self.connection._connected:
            try:
                await self.connection.send('Browser.close')
                await self.connection.dispose()
            except Exception:
                # ignore errors on browser termination process
                pass
        if self._tmp_user_data_dir and os.path.exists(self._tmp_user_data_dir):
            # Force kill chrome only when using temporary userDataDir
            # await self.waitForChromeToClose()
            self._cleanup_tmp_user_data_dir()
