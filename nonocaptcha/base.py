import asyncio
import logging
import os
import random
import yaml

from nonocaptcha import settings, package_dir

FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT)


class SafePassage(Exception):
    pass


class TryAgain(Exception):
    pass


class Clicker:
    @staticmethod
    async def click_button(button):
        click_delay = random.uniform(30, 170)
        await button.click(delay=click_delay / 1000)


class Base(Clicker):
    logger = logging.getLogger(__name__)
    if settings["main"]["debug"]:
        logger.setLevel("DEBUG")
    proc_id = 0
    headless = settings["main"]["headless"]
    keyboard_traverse = settings["main"]["keyboard_traverse"]
    proxy_protocol = settings["proxy"]["protocol"]
    page_load_timeout = settings["main"]["timeout"]["page_load"] * 1000
    deface_timeout = settings["main"]["timeout"]["deface"] * 1000
    animation_timeout = settings["main"]["timeout"]["animation"] * 1000
    speech_service = settings["speech"]["service"]
    deface_data = os.path.join(package_dir, settings["data"]["deface_html"])
    jquery_data = os.path.join(package_dir, settings["data"]["jquery"])
    override_data = os.path.join(package_dir, settings["data"]["override_js"])

    def get_frames(self):
        self.checkbox_frame = next(
            frame for frame in self.page.frames if "api2/anchor" in frame.url
        )
        self.image_frame = next(
            frame for frame in self.page.frames if "api2/bframe" in frame.url
        )

    async def click_reload_button(self):
        reload_button = await self.image_frame.J("#recaptcha-reload-button")
        await self.click_button(reload_button)

    async def check_detection(self, frame, timeout, wants_true=""):
        """Checks if "Try again later", "please solve more" modal appears
        or success"""

        if wants_true:
            wants_true = f"if({wants_true}) return true;"

        # if isinstance(wants_true, list):
        #    l = [f'if({i}) return true;' for i in wants_true]
        #    wants_true = '\n'.join(wants_true)

        func = """(function() {
    checkbox_frame = parent.window.$("iframe[src*='api2/anchor']").contents();
    image_frame = parent.window.$("iframe[src*='api2/bframe']").contents();

    var bot_header = $(".rc-doscaptcha-header-text", image_frame)
    if(bot_header.length){
        if(bot_header.text().indexOf("Try again later") > -1){
            parent.window.wasdetected = true;
            return true;
        }
    }

    var try_again_header = $(".rc-audiochallenge-error-message", image_frame)
    if(try_again_header.length){
        if(try_again_header.text().indexOf("please solve more") > -1){
            try_again_header.text('Trying again...')
            parent.window.tryagain = true;
            return true;
        }
    }

    var checkbox_anchor = $("#recaptcha-anchor", checkbox_frame);
    if(checkbox_anchor.attr("aria-checked") === "true"){
        parent.window.success = true;
        return true;
    }

})()"""
        try:
            await frame.waitForFunction(func, timeout=timeout)
        except asyncio.TimeoutError:
            raise SafePassage()
        else:
            if await frame.evaluate("parent.window.wasdetected === true;"):
                status = "detected"
            elif await frame.evaluate("parent.window.tryagain === true"):
                await frame.evaluate("parent.window.tryagain = false;")
                raise TryAgain()
            elif await frame.evaluate("parent.window.success === true"):
                status = "success"

            return {"status": status}

    def log(self, message):
        self.logger.debug(f"{self.proc_id} {message}")
