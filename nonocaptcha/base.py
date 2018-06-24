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
    
        func ="""() => {
            %s
            
            var elem_bot = parent.frames[1].document.getElementsByClassName
                ("rc-doscaptcha-header-text")[0];
            if(typeof elem_bot !== 'undefined'){
                if(elem_bot.innerText === 'Try again later'){
                    parent.window.wasdetected = true;
                    return true;
                }
            }
    
            var elem_try = parent.frames[1].document.getElementsByClassName
                ("rc-audiochallenge-error-message")[0];
            if(typeof elem_try !== 'undefined'){
                if(elem_try.innerText.indexOf('please solve more.') >= 0){
                    elem_try.parentNode.removeChild(elem_try);
                    return true;
                }
            }
            
            var elem_anchor = parent.frames[0].document.getElementById
                ("recaptcha-anchor");
            if(elem_anchor.getAttribute("aria-checked") === "true"){
                return true
            }

            
        }"""% wants_true
        try:
            await frame.waitForFunction(func, timeout=timeout * 1000)
        except:
            raise
        else:
            eval = "typeof parent.window.wasdetected !== 'undefined'"
            if await frame.evaluate(eval):
                self.log("Automation detected")
                self.detected = True
