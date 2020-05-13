#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Solver module. """

import sys
import time
import traceback

from pyppeteer.errors import NetworkError, PageError, PyppeteerError
from pyppeteer.util import merge_dict

from goodbyecaptcha import util
from goodbyecaptcha.audio import SolveAudio
from goodbyecaptcha.base import Base
from goodbyecaptcha.exceptions import SafePassage, ButtonError, IframeError, TryAgain, ResolveMoreLater
from goodbyecaptcha.image import SolveImage
from goodbyecaptcha.util import get_random_proxy


class Solver(Base):
    def __init__(self, pageurl, sitekey, loop=None, proxy=None, proxy_auth=None, options=None, **kwargs):
        self.url = pageurl
        self.sitekey = sitekey
        self.loop = loop or util.get_event_loop()
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.options = merge_dict({} if options is None else options, kwargs)

        super(Solver, self).__init__(loop=loop, proxy=proxy, proxy_auth=proxy_auth, options=options)

    async def start(self):
        """Begin solving"""
        start = time.time()
        result = None
        try:
            self.browser = await self.get_new_browser()
            await self.open_page(self.url, new_page=False)  # Use first page
            result = await self.solve()
        except NetworkError as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Network error: {ex}")
        except ResolveMoreLater as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Resolve More Captcha error: {ex}")
        except TryAgain as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Try Again error: {ex}")
        except TimeoutError as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Error timeout: {ex}")
        except PageError as ex:
            traceback.print_exc(file=sys.stdout)
            print(f"Page Error: {ex}")
        except IframeError as ex:
            print(f"IFrame error: {ex}")
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
        """Click checkbox, otherwise attempt to decipher image/audio"""
        self.log('Solvering ...')
        try:
            await self.get_frames()
        except Exception:
            raise IframeError("Problem locating reCAPTCHA frames")
        self.log('Wait for CheckBox ...')
        await self.loop.create_task(self.wait_for_checkbox())
        self.log('Click CheckBox ...')
        await self.click_checkbox()
        try:
            result = await self.loop.create_task(
                self.check_detection(self.animation_timeout))  # Detect Detection or captcha finish
        except SafePassage:
            return await self._solve()  # Start to solver
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
        """Select method solver"""
        proxy = get_random_proxy() if self.proxy == 'auto' else self.proxy
        if self.method == 'images':
            self.log('Using Image Solver')
            self.image = SolveImage(page=self.page, image_frame=self.image_frame, loop=self.loop, proxy=proxy,
                                    proxy_auth=self.proxy_auth, options=self.options)
            solve = self.image.solve_by_image
        else:
            self.log('Using Audio Solver')
            self.audio = SolveAudio(page=self.page, image_frame=self.image_frame, loop=self.loop, proxy=proxy,
                                    proxy_auth=self.proxy_auth, options=self.options)
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
            await self.click_checkbox()  # Try Click

    async def click_checkbox(self):
        """Click checkbox on page load."""
        try:
            checkbox = await self.checkbox_frame.J("#recaptcha-anchor")
            await self.click_button(checkbox)
        except Exception as ex:
            self.log(ex)
            raise ex

    async def g_recaptcha_response(self):
        """Result of captcha"""
        code = await self.page.evaluate(
            "jQuery('#g-recaptcha-response').val()")
        return code
