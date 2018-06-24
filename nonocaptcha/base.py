import logging
import random

from config import settings
from nonocaptcha.helper import wait_between


FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT)



class Clicker:
    @staticmethod
    async def click_button(button):
        click_delay = random.uniform(70, 130)
        await wait_between(2000, 4000)
        await button.click(delay=click_delay / 1000)
        


class Base(Clicker):
    logger = logging.getLogger(__name__)
    if settings["debug"]:
        logger.setLevel("DEBUG")
    
    detected = False
    
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
    
        func ="""(function() {
    %s

    checkbox_frame = parent.frames[0].document;
    image_frame = parent.frames[1].document;

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
            return true;
        }
    }
    
    var checkbox_anchor = $("#recaptcha-anchor", checkbox_frame);
    if(checkbox_anchor.attr("aria-checked") === "true"){
        return true;
    }
    
})()"""% wants_true
        try:
            await frame.waitForFunction(func, timeout=timeout * 1000)
        except:
            raise
        else:
            eval = "typeof parent.window.wasdetected !== 'undefined'"
            if await frame.evaluate(eval):
                self.log("Automation detected")
                self.detected = True
