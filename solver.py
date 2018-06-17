#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Solver module."""

import random
import asyncio
import time
import json
import tempfile

from pyppeteer import launch
from pyppeteer.util import merge_dict
from async_timeout import timeout

import util
from config import settings
from helper import wait_between
from speech import get_text
from user_agent import generate_navigator_js


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
        self._url = pageurl
        self._sitekey = sitekey
        self._proxy = proxy
        self._proxy_auth = proxy_auth

        self._detected = False
        self._headless = settings["headless"]
        self._debug = settings["debug"]

    @property
    def debug(self):
        return self._debug
        
    @property
    def headless(self):
        return self._headless

    async def start(self):
        """Start solving"""

        start = time.time()
        try:
            self.browser = await self._get_new_browser()
            self.page = await self.browser.newPage()
            if self._proxy_auth:
                await self.page.authenticate(self._proxy_auth)

            with timeout(120):
                result = await self._solve()
        except Exception as e:
            result = None
        finally:
            end = time.time()
            elapsed = end - start
            if self.debug:
                print(f"Time elapsed: {elapsed}")
            await self.browser.close()
        return result

    async def _get_new_browser(self):
        """Get new browser, set arguments from options, proxy,
        and random window size if headless.
        """

        chrome_args = [
            "--no-sandbox",
            "--disable-web-security"
        ]

        if self._headless:
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

        if self._proxy:
            chrome_args.append(f"--proxy-server=http://{self._proxy}")

        self.options.update({"headless": self.headless, "args": chrome_args})
        browser = await launch(self.options)
        return browser

    async def _cloak_navigator(self):
        """Cloaks navigator values to emulate another browser and sets
        webdriver false.
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

    async def _deface_page(self):
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
            % self._sitekey
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

    async def _goto_and_deface(self):
        """Loads page in tab, and defaces"""

        user_agent = await self._cloak_navigator()
        await self.page.setUserAgent(user_agent)
        try:
            timeout = settings["wait_timeout"]["load_timeout"]
            await self.page.goto(
                self._url, timeout=timeout * 1000, waitUntil="documentloaded"
            )

            func = await self._deface_page()
            timeout = settings["wait_timeout"]["deface_timeout"]
            await self.page.waitForFunction(func, timeout=timeout * 1000)
        except Exception as e:
            if self.debug:
                print(e)
            raise Exception(e)

    async def _solve(self):
        """Clicks checkbox, on failure it will attempt to solve the audio 
        file
        """

        await self.is_blacklisted()

        try:
            await self._goto_and_deface()
        except:
            return

        self.checkbox_frame = next(
            frame for frame in self.page.frames if "api2/anchor" in frame.url
        )

        self.image_frame = next(
            frame for frame in self.page.frames if "api2/bframe" in frame.url
        )

        if not settings["keyboard_traverse"]:
            if self.debug:
                print("Clicking checkbox")
            checkbox = await self.checkbox_frame.J("#recaptcha-anchor")
            await self.click_button(checkbox)
        else:
            self.body = await self.page.J("body")
            await self.body.press("Tab")
            await self.body.press("Enter")

        try:
            timeout = settings["wait_timeout"]["success_timeout"]
            await self._check_detection(self.checkbox_frame, timeout * 1000)
        except:
            await self._click_audio_button()
            if self._detected:
                return
            for i in range(5):
                try:
                    result = await self._solve_by_audio()
                except:
                    break
                else:
                    if self._detected:
                        break
                    if result:
                        code = await self.g_recaptcha_response()
                        if code:
                            if self.debug:
                                print("Success!")
                            return f"OK|{code}"
        else:
            code = await self.g_recaptcha_response()
            if code:
                if self.debug:
                    print("One-click success!")
                return f"OK|{code}"

    async def _click_audio_button(self):
        """Actual clicking of the audio button"""

        audio_button_elem = 'document.getElementById("recaptcha-audio-button")'
        func = f'typeof {audio_button_elem} !== "undefined"'
        try:
            timeout = settings["wait_timeout"]["audio_button_timeout"]
            await self._check_detection(
                self.image_frame, timeout * 1000, wants_true=func
            )
        except:
            if self.debug:
                print("Audio button missing")
            raise Exception("Audio button non-existent")

        if not settings["keyboard_traverse"]:
            if self.debug:
                print("Clicking audio button")
            audio_button = await self.image_frame.J("#recaptcha-audio-button")
            await self.click_button(audio_button)
        else:
            await self.body.press("Enter")

        func = (
            "typeof "
            'document.getElementsByClassName("rc-audiochallenge-tdownload-link'
            '")[0] !== "undefined"'
        )

        timeout = settings["wait_timeout"]["audio_link_timeout"]
        await self._check_detection(
            self.image_frame, timeout * 1000, wants_true=func
        )

    async def _solve_by_audio(self):
        """Types in audio response after clicking audio button and receiving an
        answer.
        """

        answer = await self._get_audio_response()
        if not answer:
            return
        response_input = await self.image_frame.J("#audio-response")
        verify_button = await self.image_frame.J("#recaptcha-verify-button")
        if self.debug:
            print("Typing answer")
        length = random.uniform(70, 130)
        await response_input.type(text=answer, delay=length)
        await asyncio.sleep(random.uniform(300, 700) / 1000)
        await response_input.press("Enter")
        # if self.debug:
        #    print("Clicking verify")
        # await self.click_button(verify_button)

        timeout = settings["wait_timeout"]["success_timeout"]
        await self._check_detection(self.checkbox_frame, timeout * 1000)
        return answer

    async def _get_audio_response(self):
        """Downloads audio files then sends to speech-to-text API for answer"""

        download_element = (
            'document.getElementsByClassName("rc-audiochallenge-tdownload-link'
            '")[0]'
        )

        audio_url = await self.image_frame.evaluate(
            f'{download_element}.getAttribute("href")'
        )

        audio_data = await util.get_page(audio_url, self._proxy, binary=True)

        if self.debug:
            print("Downloading response")
        with tempfile.NamedTemporaryFile(suffix="mp3") as tmpfile:
            await util.save_file(tmpfile.name, audio_data, binary=True)
            answer = await get_text(tmpfile.name)
            if answer:
                if self.debug:
                    print(f'Received answer "{answer}"')
                return answer
            else:
                if self.debug:
                    print("No answer, reloading audio")
                reload_button = await self.image_frame.J(
                    "#recaptcha-reload-button"
                )
                await self.click_button(reload_button)
                timeout = settings["wait_timeout"]["reload_timeout"]
                func = (
                        f'"{audio_url}" !== '
                        f'{download_element}.getAttribute("href")'
                    )
                await self._check_detection(
                    self.image_frame, timeout * 1000, wants_true=func
                )

    async def _check_detection(self, frame, timeout, wants_true=""):
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
                    parent.wasdetected = true;
                    return true;
                }
            }

            var elem_try = %s;
            if(typeof elem_try !== 'undefined'){
                if(elem_try.innerText
                    === 
                   'Multiple correct solutions required - please solve more.'){
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
            await frame.waitForFunction(func, timeout=timeout)
        except Exception as e:
            if self.debug:
                print(e)
            raise Exception(f"Element non-existent {e}")
        else:
            if await self.page.evaluate("typeof wasdetected !== 'undefined'"):
                if self.debug:
                    print("We were detected")
                self._detected = True

    async def click_button(self, button):
        click_delay = random.uniform(200, 500)
        wait_delay = random.uniform(2000, 4000)
        await asyncio.sleep(wait_delay / 1000)
        await button.click(delay=click_delay / 1000)

    async def g_recaptcha_response(self):
        func = 'document.getElementById("g-recaptcha-response").value'
        code = await self.page.evaluate(func)
        return code

    async def is_blacklisted(self):
        blocked_page = await self.browser.newPage()
        timeout = settings["wait_timeout"]["load_timeout"]
        await blocked_page.goto("https://www.google.com/search?q=my+ip",
                                waitUntil="documentloaded", timeout=timeout * 1000)
        detected_phrase = "Our systems have detected unusual traffic from your computer"
        page_content = await blocked_page.content()
        if detected_phrase in page_content:
            self._detected = True
            if self.debug:
                print("IP has been blacklisted by google")
        await blocked_page.close()
