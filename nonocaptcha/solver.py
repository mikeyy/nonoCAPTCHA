#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Solver module."""

import asyncio
import atexit
import json
import pathlib
import psutil
import random
import signal
import sys
import tempfile
import time

from async_timeout import timeout as async_timeout
from pyppeteer import launcher
from pyppeteer.util import merge_dict
from pyppeteer.browser import Browser
from pyppeteer.connection import Connection
from pyppeteer.errors import TimeoutError
from user_agent import generate_navigator_js

from config import settings
from nonocaptcha import util
from nonocaptcha.image import SolveImage
from nonocaptcha.audio import SolveAudio
from nonocaptcha.base import Base



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
        if self.proc.returncode is None and not self.chromeClosed:
            self.chromeClosed = True
            if psutil.pid_exists(self.proc.pid):
                self.proc.terminate()
                self.proc.kill()


async def launch(options, **kwargs):
    return await Launcher(options, **kwargs).launch()



class Solver(Base):
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

        self.headless = settings["headless"]
        self.gmail_accounts = {}
        self.proc_id = self.proc_count
        type(self).proc_count += 1

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
            false, inject jQuery.
        """

        jquery_js = await util.load_file(
            settings["data_files"]["jquery_js"]
        )

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
            "() => {\n%s\n%s\n%s}" % (_navigator, jquery_js, override_js)
        )

        return navigator_config["userAgent"]

    async def wait_for_deface(self):
        """Overwrite current page with reCAPTCHA widget and wait for image
        iframe to load on document before continuing.
            
        Function x is an odd hack for multiline text, but it works.
        """
        html_code = await util.load_file(settings["data_files"]["deface_html"])
        
        deface_js = (
            ("""() => {
    var x = (function () {/*
        %s
    */}).toString().match(/[^]*\/\*([^]*)\*\/\}$/)[1];

    document.open(); 
    document.write(x)
    document.close();
}
"""% html_code)% self.sitekey)

        await self.page.evaluate(deface_js)
    
        func ="""() => {
    frame = $("iframe[src*='api2/bframe']")
    $(frame).load( function() {
        window.ready_eddy = true;
    });
    if(window.ready_eddy) return true;
}"""

        timeout = settings["wait_timeout"]["deface_timeout"]
        await self.page.waitForFunction(func, timeout=timeout * 1000)

    async def goto_and_deface(self):
        """Open tab and deface page"""

        user_agent = await self.cloak_navigator()
        await self.page.setUserAgent(user_agent)
        try:
            timeout = settings["wait_timeout"]["load_timeout"]
            await self.page.goto(
                self.url, timeout=timeout * 1000, waitUntil="documentloaded"
            )
            await self.wait_for_deface()
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
        
        await self.click_checkbox()

        timeout = settings["wait_timeout"]["success_timeout"]
        try:
            await self.check_detection(self.checkbox_frame, timeout=timeout)
        except:
            return await self._solve()
        else:
            code = await self.g_recaptcha_response()
            if code:
                self.log("One-click successful")
                return f"OK|{code}"

    async def _solve(self):
        # Coming soon!
        solve_image = False
        if solve_image:
            self.image = SolveImage(self.page, self.proxy, self.proc_id)
            solve = self.image.solve_by_image
        else:
            self.audio = SolveAudio(self.page, self.proxy, self.proc_id)

            await self.wait_for_audio_button()
            await self.click_audio_button()
            solve = self.audio.solve_by_audio

        await solve()

        code = await self.g_recaptcha_response()
        if code:
            self.log("Audio response successful")
            return f"OK|{code}"

    async def click_checkbox(self):
        """Click checkbox on page load."""

        if settings["keyboard_traverse"]:
            self.body = await self.page.J("body")
            await self.body.press("Tab")
            await self.body.press("Enter")
        else:
            self.log("Clicking checkbox")
            checkbox = await self.checkbox_frame.J("#recaptcha-anchor")
            await self.click_button(checkbox)

    async def wait_for_audio_button(self):
        """Wait for audio button to appear."""

        timeout = settings["wait_timeout"]["audio_button_timeout"]
        try:
            await self.image_frame.waitForFunction(
                "$('#recaptcha-audio-button').length", timeout=timeout * 1000
            )
        except:
            self.log("Audio button missing, aborting")
            raise

    async def click_audio_button(self):
        """Click audio button after it appears."""

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

    async def g_recaptcha_response(self):
        code = await self.page.evaluate("$('#g-recaptcha-response').val()")
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
        cookie_path = settings['data_files']['cookies']
        if pathlib.Path(cookie_path).exists():
            self.gmail_accounts = await util.deserialize(cookie_path)
        if settings['gmail'] not in self.gmail_accounts:
            url = "https://accounts.google.com/Login"
            page = await self.browser.newPage()
            await page.goto(url, waitUntil="documentloaded")
            username = await page.querySelector('#identifierId')
            await username.type(settings['gmail'])
            button = await page.querySelector('#identifierNext')
            await button.click()
            await asyncio.sleep(2)  # better way to do this...
            navigation = page.waitForNavigation()
            password = await page.querySelector('#password')
            await password.type(settings['gmail_password'])
            button = await page.querySelector('#passwordNext')
            await button.click()
            await navigation
            cookies = await page.cookies()
            self.gmail_accounts[settings["gmail"]] = cookies
            util.serialize(self.gmail_accounts, cookie_path)
            await page.close()
        await self.load_cookies()

    async def load_cookies(self, account=settings["gmail"]):
        cookies = self.gmail_accounts[account]
        for c in cookies:
            await self.page.setCookie(c)
