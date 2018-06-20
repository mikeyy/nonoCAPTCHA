#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Solver module."""

import sys
import time
import json
import atexit
import psutil
import random
import signal
import asyncio
import logging
import tempfile

from pyppeteer import launcher
from pyppeteer.util import merge_dict
from pyppeteer.browser import Browser
from pyppeteer.connection import Connection
from user_agent import generate_navigator_js
from async_timeout import timeout as async_timeout

from nonocaptcha import util
from nonocaptcha.helper import wait_between
from nonocaptcha.speech import get_text

try:
    from config import settings
except:
    print("Solver can't run without a config.py file!\n"
          "Please see https://github.com/mikeyy/nonoCAPTCHA for more info.")
    
    import sys
    sys.exit(0)

FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
if settings["debug"]:
    logger.setLevel("DEBUG")


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

    async def start(self):
        """Start solving"""

        start = time.time()
        try:
            self.browser = await self.get_new_browser()
            self.page = await self.browser.newPage()
            if self.proxy_auth:
                await self.page.authenticate(self.proxy_auth)

            logger.debug("Starting solver with proxy %s", self.proxy)
            with async_timeout(120):
                result = await self.solve()
        except:
            result = None
        finally:
            end = time.time()
            elapsed = end - start
            logger.debug("Time elapsed: %s", elapsed)
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
        """ Emulate another browser's navigator properties and set webdriver
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
        func = """() => {
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
        """ Open tab and deface page """

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
            logger.debug("Checking Google search for blacklist")
            if await self.is_blacklisted():
                return

        if not await self.goto_and_deface():
            logger.debug("Problem defacing page")
            return

        self.get_frames()
        await self.click_checkbox()

        timeout = settings["wait_timeout"]["success_timeout"]
        try:
            await self.check_detection(self.checkbox_frame, timeout=timeout)
        except:
            await self.click_audio_button()
            for i in range(5):
                result = await self.solve_by_audio()
                if result:
                    code = await self.g_recaptcha_response()
                    if code:
                        logger.debug("Audio response successful")
                        return f"OK|{code}"
        else:
            code = await self.g_recaptcha_response()
            if code:
                logger.debug("One-click successful")
                return f"OK|{code}"

    async def solve_by_audio(self):
        """ Go through procedures to solve audio """

        answer = await self.get_audio_response()
        if not answer:
            return
        await self.type_audio_response(answer)
        await self.click_verify()

        timeout = settings["wait_timeout"]["success_timeout"]
        try:
            await self.check_detection(self.checkbox_frame, timeout)
        finally:
            if self.detected:
                raise
            return 1

    def get_frames(self):
        self.checkbox_frame = next(
            frame for frame in self.page.frames if "api2/anchor" in frame.url
        )

        self.image_frame = next(
            frame for frame in self.page.frames if "api2/bframe" in frame.url
        )

    async def click_checkbox(self):
        """ Click checkbox """

        if not settings["keyboard_traverse"]:
            logger.debug("Clicking checkbox")
            checkbox = await self.checkbox_frame.J("#recaptcha-anchor")
            await self.click_button(checkbox)
        else:
            self.body = await self.page.J("body")
            await self.body.press("Tab")
            await self.body.press("Enter")

    async def click_audio_button(self):
        """ Click audio button """

        if not settings["keyboard_traverse"]:
            logger.debug("Clicking audio button")
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

    async def get_audio_response(self):
        """ Download audio data then send to speech-to-text API for answer """

        download_link_element = (
            'document.getElementsByClassName("rc-audiochallenge-tdownload-link'
            '")[0]'
        )

        audio_url = await self.image_frame.evaluate(
            f'{download_link_element}.getAttribute("href")'
        )

        logger.debug("Downloading audio file")
        audio_data = await util.get_page(audio_url, self.proxy, binary=True)

        answer = None
        with tempfile.NamedTemporaryFile(suffix="mp3") as tmpfile:
            await util.save_file(tmpfile.name, audio_data, binary=True)
            answer = await get_text(tmpfile.name)

        if answer:
            logger.debug('Received answer "%s"', answer)
            return answer

        logger.debug("No answer, reloading")
        await self.click_reload_button()

        func = (
            f'"{audio_url}" !== '
            f'{download_link_element}.getAttribute("href")'
        )
        timeout = settings["wait_timeout"]["reload_timeout"]
        try:
            await self.check_detection(
                self.image_frame, timeout, wants_true=func
            )
        except:
            raise
        else:
            if self.detected:
                raise

    async def type_audio_response(self, answer):
        logger.debug("Typing audio response")
        response_input = await self.image_frame.J("#audio-response")
        length = random.uniform(70, 130)
        await response_input.type(text=answer, delay=length)

    async def click_verify(self):
        if settings["keyboard_traverse"]:
            response_input = await self.image_frame.J("#audio-response")
            logger.debug("Pressing Enter")
            await response_input.press("Enter")
        else:
            verify_button = await self.image_frame.J(
                "#recaptcha-verify-button"
            )

            logger.debug("Clicking verify")
            await self.click_button(verify_button)

    async def click_reload_button(self):
        reload_button = await self.image_frame.J("#recaptcha-reload-button")
        await self.click_button(reload_button)

    async def click_button(self, button):
        click_delay = random.uniform(70, 130)
        wait_delay = random.uniform(2000, 4000)
        await asyncio.sleep(wait_delay / 1000)
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
                logger.debug("IP has been blacklisted by Google")
                return 1
        except:
            return

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

        func = """() => {
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
        }""" % (
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
                logger.debug("Automation detected")
                self.detected = True
