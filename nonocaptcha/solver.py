#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Solver module."""

import asyncio
import atexit
import json
import logging
import psutil
import random
import signal
import sys
import tempfile
import time
import pathlib

from async_timeout import timeout as async_timeout
from user_agent import generate_navigator_js
from pyppeteer import launcher
from pyppeteer.util import merge_dict
from pyppeteer.browser import Browser
from pyppeteer.connection import Connection
from pyppeteer.errors import TimeoutError

from nonocaptcha import util
from nonocaptcha.audio import SolveAudio
from nonocaptcha.helper import wait_between
from config import settings


FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT)


class Launcher(launcher.Launcher):
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

    def waitForChromeToClose(self):
        """Terminate chrome."""
        if self.proc.returncode is not None and not self.chromeClosed:
            self.chromeClosed = True
            if psutil.pid_exists(self.proc.pid):
                self.proc.terminate()
                self.proc.kill()


async def launch(options, **kwargs):
    return await Launcher(options, **kwargs).launch()


class Solver(object):
    logger = logging.getLogger(__name__)
    if settings["debug"]:
        logger.setLevel("DEBUG")
    proc_count = 0

    def __init__(
        self,
        pageurl,
        sitekey,
        proxy=None,
        proxy_auth=None,
        options={},
        **kwargs,
    ):
        self.options = merge_dict(options, kwargs)
        self.url = pageurl
        self.sitekey = sitekey
        self.proxy = proxy
        self.proxy_auth = proxy_auth

        self.detected = False
        self.headless = settings["headless"]
        self.cookies = []
        self.proc_id = self.proc_count
        type(self).proc_count += 1

    def log(self, message):
        self.logger.debug(f'{self.proc_id} {message}')

    async def start(self):
        """Start solving"""
        
        result = None
        start = time.time()
        try:
            self.browser = await self.get_new_browser()
            self.page = await self.browser.newPage()
            if self.proxy_auth:
                await self.page.authenticate(self.proxy_auth)

            if settings['gmail']:
                await self.sign_in_to_google()
                for c in self.cookies:
                    await self.page.setCookie(c) # rethink multiple accounts

            self.log(f"Starting solver with proxy {self.proxy}")
            with async_timeout(120):
                result = await self.solve()
        except TimeoutError:
            pass  # otherwise TimeoutError floods logging output
        except BaseException as e:
            self.log(f"{e} {type(e)}")
        finally:
            end = time.time()
            elapsed = end - start
            self.log(f"Time elapsed: {elapsed}")
            await self.browser.close()
        return result

    async def get_new_browser(self):
        """Get new browser, set arguments from options, proxy,
        and random window size if headless.
        """

        chrome_args = [
            "--no-sandbox",
            "--disable-web-security",
            "--disable-gpu",
            "--disable-reading-from-canvas",
            '--cryptauth-http-host ""',
            "--disable-affiliation-based-matching",
            "--disable-answers-in-suggest",
            # "--disable-background-networking", Possibly increases detection..
            "--disable-breakpad",
            "--disable-demo-mode",
            "--disable-device-discovery-notifications",
            "--disable-java",
            "--disable-preconnect",
            # "--dns-prefetch-disable", # Discernably slower load-times
        ]

        if self.headless:
            aspect_ratio_list = ["3:2", "4:3", "5:3", "5:4", "16:9", "16:10"]
            aspect_ratio = random.choice(aspect_ratio_list)
            resolutions_file = settings["data_files"]["resolutions_json"]
            resolutions = await util.load_file(resolutions_file)
            j = json.loads(resolutions)
            resolution = random.choice(j[aspect_ratio])
            height, width = resolution.split("x")
            r = lambda: random.uniform(1, 2)
            hsize = int((float(height) / r()))
            wsize = int((float(width) / r()))
            chrome_args.append(f"--window-size={hsize},{wsize}")

        if self.proxy:
            chrome_args.append(f"--proxy-server=http://{self.proxy}")

        args = self.options.pop("args")
        args.extend(chrome_args)

        self.options.update({"headless": self.headless, "args": args})
        browser = await launch(self.options)
        return browser

    async def cloak_navigator(self):
        """Emulate another browser's navigator properties and set webdriver
            false.
        """

        override_js = await util.load_file(
            settings["data_files"]["override_js"]
        )
        navigator_config = generate_navigator_js(
            os=("linux", "mac", "win"), navigator=("chrome")
        )
        navigator_config["webdriver"] = False
        dump = json.dumps(navigator_config)
        _navigator = f"const _navigator = {dump};"
        await self.page.evaluateOnNewDocument(
            "() => {\n%s\n%s\n}" % (_navigator, override_js)
        )

        return navigator_config["userAgent"]

    async def deface_page(self):
        """This is way faster than :meth:`setContent` method.
        
        Function x is an odd hack for multiline text, but it works.
        """

        html_code = await util.load_file(settings["data_files"]["deface_html"])
        mockPage = (
            (
               """() => {
        var x = (function () {/*
            %s
        */}).toString().match(/[^]*\/\*([^]*)\*\/\}$/)[1];

        document.open(); 
        document.write(x)
        document.close();
    }"""
                % html_code
            )
            % self.sitekey
        )
        await self.page.evaluate(mockPage)
        func ="""() => {
    var frame = parent.document.getElementsByTagName('iframe')[1];
    if (typeof frame !== 'undefined') {
        frame.onload = function() {
            window.ready_eddy = true;
        }
    }
    
    if(window.ready_eddy) return true;
}"""
        return func

    async def goto_and_deface(self):
        """Open tab and deface page"""

        user_agent = await self.cloak_navigator()
        await self.page.setUserAgent(user_agent)
        try:
            timeout = settings["wait_timeout"]["load_timeout"]
            await self.page.goto(
                self.url, timeout=timeout * 1000, waitUntil="documentloaded"
            )
            func = await self.deface_page()
            timeout = settings["wait_timeout"]["deface_timeout"]
            await self.page.waitForFunction(func, timeout=timeout * 1000)
            return 1
        except:
            return

    async def solve(self):
        """Clicks checkbox, on failure it will attempt to solve the audio 
        file
        """

        if settings["check_blacklist"]:
            self.log("Checking Google search for blacklist")
            if await self.is_blacklisted():
                return

        if not await self.goto_and_deface():
            self.log("Problem defacing page")
            return

        self.get_frames()
        self.audio = SolveAudio(
            frames = (self.checkbox_frame, self.image_frame),
            check_detection = self.check_detection,
            proxy = self.proxy,
            log = self.log
        )

        await self.click_checkbox()

        timeout = settings["wait_timeout"]["success_timeout"]
        try:
            await self.check_detection(self.checkbox_frame, timeout=timeout)
        except:
            await self.click_audio_button()
            for i in range(5):
                result = await self.audio.solve_by_audio()
                if result:
                    code = await self.g_recaptcha_response()
                    if code:
                        self.log("Audio response successful")
                        return f"OK|{code}"
        else:
            code = await self.g_recaptcha_response()
            if code:
                self.log("One-click successful")
                return f"OK|{code}"

    def get_frames(self):
        self.checkbox_frame = next(
            frame for frame in self.page.frames if "api2/anchor" in frame.url
        )

        self.image_frame = next(
            frame for frame in self.page.frames if "api2/bframe" in frame.url
        )

    async def click_checkbox(self):
        """Click checkbox"""

        if not settings["keyboard_traverse"]:
            self.log("Clicking checkbox")
            checkbox = await self.checkbox_frame.J("#recaptcha-anchor")
            await self.click_button(checkbox)
        else:
            self.body = await self.page.J("body")
            await self.body.press("Tab")
            await self.body.press("Enter")

    async def click_audio_button(self):
        """Click audio button"""

        if not settings["keyboard_traverse"]:
            self.log("Clicking audio button")
            audio_button = await self.image_frame.J("#recaptcha-audio-button")
            await self.click_button(audio_button)
        else:
            await self.body.press("Enter")

        timeout = settings["wait_timeout"]["audio_button_timeout"]
        try:
            await self.check_detection(self.image_frame, timeout)
        except:
            pass
        finally:
            if self.detected:
                raise

    async def click_button(self, button):
        click_delay = random.uniform(70, 130)
        await wait_between(2000, 4000)
        await button.click(delay=click_delay / 1000)

    async def g_recaptcha_response(self):
        func = 'document.getElementById("g-recaptcha-response").value'
        code = await self.page.evaluate(func)
        return code

    async def is_blacklisted(self):
        try:
            timeout = settings["wait_timeout"]["load_timeout"]
            url = "https://www.google.com/search?q=my+ip&hl=en"
            response = await util.get_page(
                url, proxy=self.proxy, timeout=timeout
            )
            detected_phrase = (
                "Our systems have detected unusual traffic "
                "from your computer"
            )
            if detected_phrase in response:
                self.log("IP has been blacklisted by Google")
                return 1
        except:
            return

    async def sign_in_to_google(self):
        cookie_path = settings['data_files']['cookies'] + '/google_account'
        if not pathlib.Path(cookie_path).exists():
            url = "https://accounts.google.com/Login"
            page = await self.browser.newPage()
            await page.goto(url, waitUntil="documentloaded")
            username = await page.querySelector('#identifierId')
            await username.type(settings['gmail'])
            button = await page.querySelector('#identifierNext')
            await button.click()
            await asyncio.sleep(2) # better way to do this...
            navigation = page.waitForNavigation()
            password = await page.querySelector('#password')
            await password.type(settings['gmail_password'])
            button = await page.querySelector('#passwordNext')
            await button.click()
            await navigation
            self.cookies = await page.cookies()
            util.serialize(self.cookies, cookie_path)
            await page.close()
        else:
            self.cookies = util.deserialize(cookie_path)

    async def check_detection(self, frame, timeout, wants_true=""):
        """Checks if "Try again later" modal appears"""

        # I got lazy here
        bot_header = (
            "parent.frames[1].document.getElementsByClassName"
            '("rc-doscaptcha-header-text")[0]'
        )
        try_again_header = (
            "parent.frames[1].document.getElementsByClassName"
            '("rc-audiochallenge-error-message")[0]'
        )
        checkbox = (
            'parent.frames[0].document.getElementById("recaptcha-anchor")'
        )

        if wants_true:
            wants_true = f"if({wants_true}) return true;"

        # if isinstance(wants_true, list):
        #    l = [f'if({i}) return true;' for i in wants_true]
        #    wants_true = '\n'.join(wants_true)

        func ="""() => {
            %s
            
            var elem_bot = %s;
            if(typeof elem_bot !== 'undefined'){
                if(elem_bot.innerText === 'Try again later'){
                    window.wasdetected = true;
                    return true;
                }
            }

            var elem_try = %s;
            if(typeof elem_try !== 'undefined'){
                if(elem_try.innerText.indexOf('please solve more.') >= 0){
                    return true;
                }
            }
            
            var elem_anchor = %s;
            if(elem_anchor.getAttribute("aria-checked") === "true"){
                return true
            }
        }"""% (
            wants_true,
            bot_header,
            try_again_header,
            checkbox,
        )
        try:
            await frame.waitForFunction(func, timeout=timeout * 1000)
        except:
            raise
        else:
            eval = "typeof wasdetected !== 'undefined'"
            if await self.image_frame.evaluate(eval):
                self.log("Automation detected")
                self.detected = True
