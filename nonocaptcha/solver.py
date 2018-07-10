#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Solver module."""

import asyncio
import json
import pathlib
import time
import sys

from asyncio import TimeoutError, CancelledError
from pyppeteer.util import merge_dict
from user_agent import generate_navigator_js

from nonocaptcha.base import Base, Detected, SafePassage, Success
from nonocaptcha.audio import SolveAudio
from nonocaptcha.image import SolveImage
from nonocaptcha.launcher import Launcher
from nonocaptcha import util


class ButtonError(Exception):
    pass


class DefaceError(Exception):
    pass


class PageError(Exception):
    pass


class Solver(Base):
    browser = None
    launcher = None
    proc_count = 0
    proc = None

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
        self.proxy = f"{self.proxy_protocol}://{proxy}" if proxy else proxy
        self.proxy_auth = proxy_auth

        self.proc_id = self.proc_count
        type(self).proc_count += 1

    async def start(self):
        """Begin solving"""
        result = None
        start = time.time()
        try:
            self.browser = await self.get_new_browser()
            target = [t for t in self.browser.targets() if await t.page()][0]
            self.page = await target.page()
            if self.proxy_auth:
                await self.page.authenticate(self.proxy_auth)
            self.log(f"Starting solver with proxy {self.proxy}")
            await self.goto()
            await self.deface()
            result = await self.solve()
        except BaseException as e:
            self.log(f"{e} {type(e)}")
        finally:
            end = time.time()
            elapsed = end - start
            self.log(f"Time elapsed: {elapsed}")
            if self.browser:
                await self.browser.close()
        return result

    async def get_new_browser(self):
        """Get a new browser, set proxy and arguments"""
        chrome_args = []
        if self.proxy:
            chrome_args.append(f"--proxy-server={self.proxy}")
        args = self.options.pop("args")
        args.extend(chrome_args)
        self.options.update({"headless": self.headless, "args": args})
        self.launcher = Launcher(self.options)
        browser = await self.launcher.launch()
        return browser

    async def cloak_navigator(self):
        """Emulate another browser's navigator properties and set webdriver
           false, inject jQuery.
        """
        jquery_js = await util.load_file(self.jquery_data)
        override_js = await util.load_file(self.override_data)
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
        html_code = await util.load_file(self.deface_data)
        deface_js = (
            (
                """() => {
    var x = (function () {/*
        %s
    */}).toString().match(/[^]*\/\*([^]*)\*\/\}$/)[1];
    document.open();
    document.write(x)
    document.close();
}
"""
                % html_code
            )
            % self.sitekey
        )
        await self.page.evaluate(deface_js)
        func = """() => {
    frame = $("iframe[src*='api2/bframe']")
    $(frame).load( function() {
        window.ready_eddy = true;
    });
    if(window.ready_eddy){
        return true;
    }
}"""
        await self.page.waitForFunction(func, timeout=self.deface_timeout)

    async def goto(self):
        """Navigate to address"""
        user_agent = await self.cloak_navigator()
        await self.page.setUserAgent(user_agent)
        try:
            await self.page.goto(
                self.url,
                timeout=self.page_load_timeout,
                waitUntil="documentloaded",
            )
        except TimeoutError:
            raise PageError("Problem loading page")

    async def deface(self):
        try:
            await self.wait_for_deface()
        except TimeoutError:
            raise DefaceError("Problem defacing page")

    async def solve(self):
        """Click checkbox, on failure it will attempt to decipher the audio
           file
        """
        self.get_frames()
        await self.wait_for_checkbox()
        await self.click_checkbox()
        try:
            result = await self.check_detection(
                self.checkbox_frame, timeout=self.animation_timeout
            )
        except SafePassage:
            return await self._solve()
        else:
            if result["status"] == "success":
                code = await self.g_recaptcha_response()
                if code:
                    result["code"] = code
                    return result
            else:
                return result

    async def _solve(self):
        # Coming soon...
        solve_image = False
        if solve_image:
            self.image = SolveImage(self.page, self.proxy, self.proc_id)
            solve = self.image.solve_by_image
        else:
            self.audio = SolveAudio(self.page, self.proxy, self.proc_id)
            await self.wait_for_audio_button()
            result = await self.click_audio_button()
            if isinstance(result, dict):
                if result["status"] == "detected":
                    return result
            solve = self.audio.solve_by_audio

        result = await solve()
        if result["status"] == "success":
            code = await self.g_recaptcha_response()
            if code:
                result["code"] = code
                return result
        else:
            return result

    async def wait_for_checkbox(self):
        """Wait for audio button to appear."""
        try:
            await self.checkbox_frame.waitForFunction(
                "$('#recaptcha-anchor').length", timeout=self.animation_timeout
            )
        except ButtonError:
            raise ButtonError("Checkbox missing, aborting")

    async def click_checkbox(self):
        """Click checkbox on page load."""
        if self.keyboard_traverse:
            self.body = await self.page.J("body")
            await self.body.press("Tab")
            await self.body.press("Enter")
        else:
            self.log("Clicking checkbox")
            checkbox = await self.checkbox_frame.J("#recaptcha-anchor")
            await self.click_button(checkbox)

    async def wait_for_audio_button(self):
        """Wait for audio button to appear."""
        try:
            await self.image_frame.waitForFunction(
                "$('#recaptcha-audio-button').length",
                timeout=self.animation_timeout,
            )
        except ButtonError:
            raise ButtonError("Audio button missing, aborting")

    async def click_audio_button(self):
        """Click audio button after it appears."""
        if self.keyboard_traverse:
            await self.body.press("Enter")
        else:
            self.log("Clicking audio button")
            audio_button = await self.image_frame.J("#recaptcha-audio-button")
            await self.click_button(audio_button)

        try:
            result = await self.check_detection(
                self.image_frame, self.animation_timeout
            )
        except SafePassage:
            pass
        else:
            return result

    async def g_recaptcha_response(self):
        code = await self.page.evaluate("$('#g-recaptcha-response').val()")
        return code
