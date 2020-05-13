#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Base module. """
import asyncio
import logging
import os
import random
import sys
import traceback
from shutil import copyfile

import fuckcaptcha as fucking
from pyppeteer.errors import TimeoutError, PageError, PyppeteerError, NetworkError
from pyppeteer.launcher import Launcher
from pyppeteer.util import merge_dict
from pyppeteer_stealth import stealth

from goodbyecaptcha import package_dir
from goodbyecaptcha.exceptions import SafePassage, TryAgain
from goodbyecaptcha.util import patch_pyppeteer, get_event_loop, load_file, get_random_proxy

logging.basicConfig(format="%(asctime)s %(message)s")

try:
    import yaml

    yaml.warnings({'YAMLLoadWarning': False})

    with open("goodbyecaptcha.yaml") as f:
        settings = yaml.load(f)
except FileNotFoundError:
    print(
        "Solver can't run without a configuration file!\n"
        "An example (goodbyecaptcha.example.yaml) has been copied to your folder."
    )

    copyfile(
        f"{package_dir}/goodbyecaptcha.example.yaml", "goodbyecaptcha.example.yaml")
    sys.exit(0)


class Base:
    """Base control Pyppeteer"""

    browser = None
    launcher = None
    page = None
    page_index = 0
    loop = None

    # Import configurations
    logger = logging.getLogger(__name__)
    debug = settings["debug"]
    if debug:
        logger.setLevel("DEBUG")
    headless = settings["headless"]
    method = settings["method"]
    keyboard_traverse = settings["keyboard_traverse"]
    page_load_timeout = settings["timeout"]["page_load"] * 1000
    click_timeout = settings["timeout"]["click"] * 1000
    animation_timeout = settings["timeout"]["animation"] * 1000
    speech_service = settings["speech"]["service"]
    speech_secondary_service = settings["speech"]["secondary_service"]
    jquery_data = os.path.join(package_dir, settings["data"]["jquery_js"])
    pictures = os.path.join(package_dir, settings['data']['pictures'])

    def __init__(self, loop=None, proxy=None, proxy_auth=None, options=None, **kwargs):
        self.options = merge_dict({} if options is None else options, kwargs)
        self.loop = loop or get_event_loop()
        self.proxy = proxy
        self.proxy_auth = proxy_auth

        patch_pyppeteer()  # Patch Pyppeter (Fix InvalidStateError and Download Chrome)

    async def get_frames(self):
        """Get frames to checkbox and image_frame of reCaptcha"""
        self.checkbox_frame = next(frame for frame in self.page.frames if "api2/anchor" in frame.url)
        self.image_frame = next(frame for frame in self.page.frames if "api2/bframe" in frame.url)

    async def click_reload_button(self):
        """Click reload button"""
        self.log('Click reload ...')
        reload_button = await self.image_frame.J("#recaptcha-reload-button")
        await self.click_button(reload_button)
        await asyncio.sleep(self.click_timeout / 1000)  # Wait for animations (Change other images)

    async def check_detection(self, timeout):
        """Checks if "Try again later", "please solve more" modal appears or success"""

        func = """(function() {
    checkbox_frame = parent.window.jQuery(
        "iframe[src*='api2/anchor']").contents();
    image_frame = parent.window.jQuery(
        "iframe[src*='api2/bframe']").contents();

    var bot_header = jQuery(".rc-doscaptcha-header-text", image_frame)
    if(bot_header.length){
        if(bot_header.text().indexOf("Try again later") > -1){
            parent.window.wasdetected = true;
            return true;
        }
    }

    var try_again_header = jQuery(
        ".rc-audiochallenge-error-message", image_frame)
    if(try_again_header.length){
        if(try_again_header.text().indexOf("please solve more") > -1){
            try_again_header.text('Trying again...')
            parent.window.tryagain = true;
            return true;
        }
    }

    var checkbox_anchor = jQuery(".recaptcha-checkbox", checkbox_frame);
    if(checkbox_anchor.attr("aria-checked") === "true"){
        parent.window.success = true;
        return true;
    }

})()"""
        try:
            await self.page.waitForFunction(func, timeout=timeout)
        except asyncio.TimeoutError:
            raise SafePassage()
        except Exception as ex:
            self.log('FATAL ERROR: {0}'.format(ex))
        else:
            status = '?'
            if await self.page.evaluate("parent.window.wasdetected === true;"):
                status = "detected"
            elif await self.page.evaluate("parent.window.success === true"):
                status = "success"
            elif await self.page.evaluate("parent.window.tryagain === true"):
                await self.page.evaluate("parent.window.tryagain = false;")
                raise TryAgain()
            return {"status": status}

    async def click_verify(self):
        """Click button of Verify"""
        self.log('Verifying ...')
        element = await self.image_frame.querySelector('#recaptcha-verify-button')
        try:
            await self.click_button(element)
            await asyncio.sleep(self.click_timeout / 1000)  # Wait for animations (Change other images)
        except Exception as ex:
            self.log(ex)
            raise Exception(ex)

    async def click_button(self, button):
        """Click button object"""
        if self.keyboard_traverse:
            bb = await button.boundingBox()
            await self.page.mouse.move(
                random.uniform(0, 800),
                random.uniform(0, 600),
                steps=int(random.uniform(40, 90))
            )
            await self.page.mouse.move(
                bb["x"], bb["y"], steps=int(random.uniform(40, 90))
            )
            await button.hover()
            await asyncio.sleep(random.uniform(0, 2))
        click_delay = random.uniform(30, 170)
        await button.click(delay=click_delay)

    async def open_page(self, url, cookies=None, new_page=True):
        """Create new page"""
        if new_page:
            self.page_index += 1  # Add Actual Index
            self.page = await self.browser.newPage()
        if self.proxy_auth and self.proxy:
            await self.page.authenticate(self.proxy_auth)
            self.log(f"Open page with proxy {self.proxy}")
        await self.set_bypass_csp()  # Set Bypass Enable
        await self.set_cookies(cookies)  # Set Cookies
        await self.on_goto()
        await stealth(self.page)  # Headless Browser prevent detection
        await self.goto(url)  # Go to page
        await self.on_start()

    async def goto(self, url):
        """Navigate to address"""
        jquery_js = await load_file(self.jquery_data)
        await self.page.evaluateOnNewDocument("() => {\n%s}" % jquery_js)  # Inject JQuery
        await fucking.bypass_detections(self.page)  # bypass reCAPTCHA detection in pyppeteer
        retry = 3  # Go to Page and Retry 3 times
        while True:
            try:
                await self.loop.create_task(self.page.goto(
                    url,
                    timeout=self.page_load_timeout * 1000,
                    waitUntil=["networkidle0", "domcontentloaded"]))
                break
            except asyncio.TimeoutError as ex:
                traceback.print_exc(file=sys.stdout)
                self.log('Error timeout: ' + str(ex) + ' retry ' + str(retry))
                if retry > 0:
                    retry -= 1
                else:
                    raise TimeoutError("Page loading timed-out")
            except PyppeteerError as ex:
                traceback.print_exc(file=sys.stdout)
                self.log(f"Pyppeteer error: {ex}")
                if retry > 0:
                    retry -= 1
                else:
                    raise ex
            except Exception as ex:
                traceback.print_exc(file=sys.stdout)
                self.log('Error unexpected: ' + str(ex) + ' retry ' + str(retry))
                if retry > 0:
                    retry -= 1
                else:
                    raise PageError(f"Page raised an error: `{ex}`")

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
        self.options.update({
            "headless": self.headless,
            "args": args,
            #  Silence Pyppeteer logs
            "logLevel": "CRITICAL"})
        self.launcher = Launcher(self.options)
        browser = await self.launcher.launch()
        self.page = (await browser.pages())[0]  # Set first page
        return browser

    async def page_switch(self, index=0):
        """Switch actual page"""
        self.page = (await self.browser.pages())[index]  # Set Actual Page
        self.page_index = index  # Update index
        await self.page.bringToFront()  # Focus new page

    async def block_images_css(self):
        """Reject requests to all image and css resource types"""

        async def handle_request(request):
            try:
                if request.resourceType == 'image' and request.resourceType == 'stylesheet':
                    await request.abort()
                else:
                    await request.continue_()
            except NetworkError:
                pass

        await self.page.setRequestInterception(True)  # Enable interception
        self.page.on('request', handle_request)

    async def set_cookies(self, cookies=None):
        """Set cookie list to current page"""
        if cookies:
            for cookie in cookies:
                cookie['url'] = self.page.url
                await self.page.setCookie(cookie)

    async def wait_load(self, waitUntil='load'):
        """Wait for Navigation"""
        await self.page.waitForNavigation({'waitUntil': waitUntil})

    async def cleanup(self):
        """Kill Browser"""
        if self.launcher:
            await self.launcher.killChrome()
            self.log('Browser closed')

    async def set_bypass_csp(self):
        """Enable bypassing of page's Content-Security-Policy."""
        await self.page._client.send("Page.setBypassCSP", {'enabled': True})

    @staticmethod
    def enter_after_text(text=None):
        """Insert Enter after of text"""
        from six import unichr
        return text + ''.join(map(unichr, [13])) if text else ''.join(map(unichr, [13]))

    # Events
    async def on_goto(self):
        """Run before to open URL"""
        pass

    async def on_start(self):
        """Run after to open URL"""
        pass

    async def on_finish(self):
        """Run after to finish the process"""
        pass

    def log(self, message):
        self.logger.debug(f"[{self.page_index}] {message}")
