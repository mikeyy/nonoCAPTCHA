#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Solver module. """

import asyncio
import random
import sys
import time
import traceback

from pyppeteer.errors import NetworkError, PageError, PyppeteerError
from pyppeteer.util import merge_dict

from goodbyecaptcha import util
from goodbyecaptcha.audio import SolveAudio
from goodbyecaptcha.base import Base
from goodbyecaptcha.exceptions import SafePassage, ButtonError, IframeError
from goodbyecaptcha.image import SolveImage
from goodbyecaptcha.util import get_random_proxy


class Solver(Base):
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
        self.url = pageurl
        self.sitekey = sitekey
        self.loop = loop or util.get_event_loop()
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.enable_injection = enable_injection
        self.retain_source = retain_source
        self.options = merge_dict({} if options is None else options, kwargs)

        super(Solver, self).__init__(loop=loop, proxy=proxy, proxy_auth=proxy_auth, options=options)

    async def start(self):
        """Begin solving"""
        start = time.time()
        result = None
        try:
            self.browser = await self.get_new_browser()
            # if self.enable_injection:
            #    await self.inject_widget()
            await self.open_page(self.url, new_page=False)  # Use first page
            await self.wait_for_frames()
            result = await self.solve()
        except NetworkError as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Network error: {ex}")
        except TimeoutError as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Error timeout: {ex}")
        except PageError as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Page Error: {ex}")
        except PyppeteerError as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Pyppeteer error: {ex}")
        except Exception as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Error unexpected: {ex}")
        finally:
            if isinstance(result, dict):
                status = result['status'].capitalize()
                print(f"Result: {status}")
            elapsed = time.time() - start
            print(f"Time elapsed: {elapsed}")
            return result

    async def solve(self):
        """Click checkbox, otherwise attempt to decipher audio"""
        self.log('Solvering ...')
        await self.get_frames()
        self.log('Wait for CheckBox ...')
        await self.loop.create_task(self.wait_for_checkbox())
        self.log('Click CheckBox ...')
        await self.click_checkbox()
        try:
            result = await self.loop.create_task(self.check_detection(self.animation_timeout))
        except SafePassage:
            return await self._solve()
        else:
            if result["status"] == "success":
                """Send Data to Buttom"""
                code = await self.g_recaptcha_response()
                if code:
                    result["code"] = code
                    return result
            else:
                return result

    async def _solve(self):
        # Coming soon...
        self.log('Solving ...')
        proxy = get_random_proxy() if self.proxy == 'auto' else self.proxy
        if self.method == 'images':
            self.log('Use Image Solver')
            self.image = SolveImage(
                self.page,
                self.image_frame,
                self.loop,
                proxy,
                self.proxy_auth,
                self.options)
            solve = self.image.solve_by_image
        else:
            self.log('Use Audo Solver')
            self.audio = SolveAudio(
                self.page,
                self.loop,
                proxy,
                self.proxy_auth,
                self.options)
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

    async def inject_widget(self):
        def insert(source="<html><head></head><body></body></html>"):
            head_index = source.find('</head>')
            source = source[:head_index] + script_tag + source[head_index:]
            body_index = source.find('</body>')
            return source[:body_index] + widget_code + source[body_index:]

        async def handle_request(request):
            if request.url == self.url:
                if self.retain_source:
                    source = await util.get_page(self.url)
                    filters = ['grecaptcha.render', 'g-recaptcha']
                    if not [filter for filter in filters if filter in source]:
                        source = insert(source)
                else:
                    source = insert()
                await request.respond({
                    'status': 200,
                    'contentType': 'text/html',
                    'body': source})
            else:
                await request.continue_()

        recaptcha_source = "https://www.google.com/recaptcha/api.js?hl=en"
        script_tag = f"<script src={recaptcha_source} async defer></script>"
        widget_code = (f"<div class=g-recaptcha data-sitekey={self.sitekey}>"
                       "</div>")
        await self.page.setRequestInterception(True)  # Enable interception
        self.page.on('request', handle_request)

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
