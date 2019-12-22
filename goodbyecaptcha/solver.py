#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Solver module. """

import asyncio
import random
import sys
import time
import traceback

import fuckcaptcha as fucking
from pyppeteer.launcher import Launcher
from pyppeteer.util import merge_dict

from goodbyecaptcha import util
from goodbyecaptcha.audio import SolveAudio
from goodbyecaptcha.base import Base
from goodbyecaptcha.exceptions import (SafePassage, ButtonError, IframeError, PageError)
from goodbyecaptcha.image import SolveImage
from goodbyecaptcha.util import get_random_proxy


class Solver(Base):
    browser = None
    launcher = None
    proc_count = 0
    proc = None

    def __init__(
            self,
            pageurl,
            sitekey,
            loop=None,
            proxy=None,
            proxy_auth=None,
            options=None,
            enable_injection=True,  # Required for pages that don't initially
            # render the widget. BROKEN, this is a noop
            retain_source=True,  # Pre-load page source and insert widget code.
            # Useful for bypassing high-security thresholds.
            # This can cause problems if the page has a widget
            # already or doesn't include a </body> tag.
            **kwargs
    ):
        if options is None:
            options = {}
        self.options = merge_dict(options, kwargs)
        self.url = pageurl
        self.sitekey = sitekey
        self.loop = loop or util.get_event_loop()
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.enable_injection = enable_injection
        self.retain_source = retain_source
        self.proc_id = self.proc_count
        self.method = 'audio'  # Default Method
        type(self).proc_count += 1

    async def start(self):
        """Begin solving"""
        start = time.time()
        result = None
        try:
            self.browser = await self.get_new_browser()
            self.page = await self.browser.newPage()
            if self.method != 'images':
                await self.block_images()
            if self.proxy_auth:
                await self.page.authenticate(self.proxy_auth)
            self.log(f"Starting solver with proxy {self.proxy}")
            await self.set_bypass_csp()
            await self.on_goto()
            await self.goto()
            await self.on_start()
            await self.wait_for_frames()
            result = await self.solve()
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            raise e
        except BaseException as e:
            print(traceback.format_exc())
            self.log(f"{e} {type(e)}")
        finally:
            if isinstance(result, dict):
                status = result['status'].capitalize()
                self.log(f"Result: {status}")
                # await self.click_send_form_buttom()
            end = time.time()
            elapsed = end - start
            await self.on_finish()
            await self.cleanup()
            self.log(f"Time elapsed: {elapsed}")
            return result

    async def block_images(self):
        async def handle_request(request):
            if request.resourceType == 'image':
                await request.abort()
            else:
                await request.continue_()

        await self.enable_interception()
        self.page.on('request', handle_request)

    async def enable_interception(self):
        await self.page.setRequestInterception(True)

    async def cleanup(self):
        if self.launcher:
            await self.launcher.killChrome()
            self.log('Browser closed')

    async def set_bypass_csp(self):
        await self.page._client.send("Page.setBypassCSP", {'enabled': True})

    async def get_new_browser(self):
        """Get a new browser, set proxy and arguments"""
        args = [
            '--cryptauth-http-host ""',
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
            '--disable-setuid-sandbox',
            '--disable-sync',
            '--disable-translate',
            '--disable-web-security',
            '--disable-webgl',
            '--metrics-recording-only',
            '--no-first-run',
            '--safebrowsing-disable-auto-update',
            '--no-sandbox',
            # Automation arguments
            '--enable-automation',
            '--password-store=basic',
            '--use-mock-keychain']
        if self.proxy:
            if self.proxy == 'auto':
                self.proxy = get_random_proxy()
            args.append(f"--proxy-server={self.proxy}")
        if "args" in self.options:
            args.extend(self.options.pop("args"))
        if "headless" in self.options:
            self.headless = self.options["headless"]
        if "method" in self.options:
            self.method = self.options["method"]
        self.options.update({
            "headless": self.headless,
            "args": args,
            #  Silence Pyppeteer logs
            "logLevel": "CRITICAL"})
        self.launcher = Launcher(self.options)
        browser = await self.launcher.launch()
        return browser

    async def deface(self):
        """ ***DEPRECATED***
        Create a DIV element and append to current body for explicit loading
        of reCAPTCHA widget.

        Websites toggled to highest-security will most often fail, such as
        Google reCAPTCHA's demo page. Looking for alternatives for
        circumvention.
        """
        deface_js = (
                """() => {
    widget = jQuery("<div id=recaptcha-widget>").appendTo("body");
    parent.window.recapReady = function(){
        grecaptcha.render(document.getElementById('recaptcha-widget'), {
            sitekey: '%s',
            callback: function () {
                console.log('recaptcha callback');
            }
        });
    }
}""" % self.sitekey)
        await self.page.evaluate(deface_js)
        recaptcha_url = ("https://www.google.com/recaptcha/api.js"
                         "?onload=recapReady&render=explicit")
        await self.page.addScriptTag(url=recaptcha_url)

    async def wait_for_frames(self):
        try:
            """Wait for image iframe to appear on dom before continuing."""
            func = """() => {
        frame = jQuery("iframe[src*='api2/bframe']")
        jQuery(frame).load( function() {
            window.ready_eddy = true;
        });
        if(window.ready_eddy){
            return true;
        }
    }"""
            await self.page.waitForFunction(func, timeout=self.iframe_timeout)
        except asyncio.TimeoutError:
            raise IframeError("Problem locating reCAPTCHA frames")

    async def goto(self):
        """Navigate to address"""
        jquery_js = await util.load_file(self.jquery_data)
        await self.page.evaluateOnNewDocument("() => {\n%s}" % jquery_js)
        await fucking.bypass_detections(self.page)
        try:
            await self.loop.create_task(
                self.page.goto(
                    self.url,
                    timeout=self.page_load_timeout,
                    waitUntil="domcontentloaded", ))
        except asyncio.TimeoutError:
            raise PageError("Page loading timed-out")
        except Exception as exc:
            raise PageError(f"Page raised an error: `{exc}`")

    async def solve(self):
        """Click checkbox, otherwise attempt to decipher audio"""
        self.log('Solvering ...')
        await self.get_frames()
        self.log('Wait for CheckBox ...')
        await self.loop.create_task(self.wait_for_checkbox())
        self.log('Click CheckBox ...')
        await self.click_checkbox()
        try:
            result = await self.loop.create_task(
                self.check_detection(self.animation_timeout))
        except SafePassage:
            return await self._solve()
        else:
            if result["status"] == "success":
                """Send Data to Buttom"""
                # await self.loop.create_task(self.wait_for_send_button())
                # await self.click_send_buttom()
                code = await self.g_recaptcha_response()
                if code:
                    result["code"] = code
                    return result
            else:
                return result

    async def _solve(self):
        # Coming soon...
        self.log('Solving ...')
        if self.proxy == 'auto':
            proxy = get_random_proxy()
        else:
            proxy = self.proxy
        if self.method == 'images':
            self.log('Use Image Solver')
            self.image = SolveImage(
                self.page,
                self.image_frame,
                proxy,
                self.proxy_auth,
                self.proc_id)
            solve = self.image.solve_by_image
        else:
            self.log('Use Audo Solver')
            self.audio = SolveAudio(
                self.page,
                self.loop,
                proxy,
                self.proxy_auth,
                self.proc_id)
            self.log('Wait for Audio Buttom ...')
            await self.loop.create_task(self.wait_for_audio_button())
            for _ in range(int(random.uniform(3, 6))):
                await self.click_tile()
            await asyncio.sleep(random.uniform(1, 2))
            self.log('Clicking Audio Buttom ...')
            result = await self.click_audio_button()
            if isinstance(result, dict):
                if result["status"] == "detected":
                    return result
            solve = self.audio.solve_by_audio

        result = await self.loop.create_task(solve())
        if result["status"] == "success":
            code = await self.g_recaptcha_response()
            if code:
                result["code"] = code
                return result
        else:
            return result

    async def wait_for_checkbox(self):
        """Wait for checkbox to appear."""
        try:
            await self.checkbox_frame.waitForFunction(
                "jQuery('#recaptcha-anchor').length",
                timeout=self.animation_timeout)
        except ButtonError:
            raise ButtonError("Checkbox missing, aborting")
        except Exception as ex:
            self.log(ex)
            # Try Click
            await self.click_checkbox()

    async def click_checkbox(self):
        """Click checkbox on page load."""
        try:
            checkbox = await self.checkbox_frame.J("#recaptcha-anchor")
            await self.click_button(checkbox)
        except Exception as ex:
            self.log(ex)
            raise Exception(ex)

    async def click_tile(self):
        self.log("Clicking random tile")
        tiles = await self.image_frame.JJ(".rc-imageselect-tile")
        await self.click_button(random.choice(tiles))

    async def wait_for_audio_button(self):
        """Wait for audio button to appear."""
        try:
            await self.image_frame.waitForFunction(
                "jQuery('#recaptcha-audio-button').length",
                timeout=self.animation_timeout)
        except ButtonError:
            raise ButtonError("Audio button missing, aborting")
        except Exception as ex:
            self.log(ex)
            raise Exception(ex)

    async def click_audio_button(self):
        """Click audio button after it appears."""
        audio_button = await self.image_frame.J("#recaptcha-audio-button")
        await self.click_button(audio_button)
        try:
            result = await self.check_detection(self.animation_timeout)
        except SafePassage:
            pass
        else:
            return result

    async def g_recaptcha_response(self):
        code = await self.page.evaluate(
            "jQuery('#g-recaptcha-response').val()")
        return code

    async def click_send_form_buttom(self):
        await self.page.click("input[name='send_form']")
        await self.page.waitForNavigation()

    # Events
    async def on_goto(self):
        pass

    async def on_start(self):
        pass

    async def on_finish(self):
        pass
