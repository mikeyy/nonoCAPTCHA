#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Base module. """

import asyncio
import logging
import os
import random
from time import sleep

from goodbyecaptcha import package_dir
from goodbyecaptcha.exceptions import SafePassage, TryAgain

FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT)

try:
    import yaml

    with open("goodbyecaptcha.yaml") as f:
        settings = yaml.load(f)
except FileNotFoundError:
    print(
        "Solver can't run without a configuration file!\n"
        "An example (goodbyecaptcha.example.yaml) has been copied to your folder."
    )

    import sys
    from shutil import copyfile

    copyfile(
        f"{package_dir}/goodbyecaptcha.example.yaml", "goodbyecaptcha.example.yaml")
    sys.exit(0)


class Clicker:
    async def click_button(self, button):
        if self.method != 'images':
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
            await asyncio.sleep(random.uniform(1, 3))
        click_delay = random.uniform(30, 170)
        await button.click(delay=click_delay)


class Base(Clicker):
    logger = logging.getLogger(__name__)
    if settings["debug"]:
        logger.setLevel("DEBUG")
    proc_id = 0
    headless = settings["headless"]
    should_block_images = settings["block_images"]
    page_load_timeout = settings["timeout"]["page_load"] * 1000
    iframe_timeout = settings["timeout"]["iframe"] * 1000
    animation_timeout = settings["timeout"]["animation"] * 1000
    speech_service = settings["speech"]["service"]
    speech_secondary_service = settings["speech"]["secondary_service"]
    deface_data = os.path.join(package_dir, settings["data"]["deface_html"])
    jquery_data = os.path.join(package_dir, settings["data"]["jquery_js"])
    override_data = os.path.join(package_dir, settings["data"]["override_js"])

    async def get_frames(self):
        self.checkbox_frame = next(
            frame for frame in self.page.frames if "api2/anchor" in frame.url
        )
        self.image_frame = next(
            frame for frame in self.page.frames if "api2/bframe" in frame.url
        )

    async def click_reload_button(self):
        self.log('Click reload ...')
        sleep(self.animation_timeout / 1000)
        reload_button = await self.image_frame.J("#recaptcha-reload-button")
        await self.click_button(reload_button)

    async def check_detection(self, timeout):
        """Checks if "Try again later", "please solve more" modal appears
        or success"""

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

    def log(self, message):
        self.logger.debug(f"{self.proc_id} {message}")
