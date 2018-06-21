import random

from config import settings
from nonocaptcha.helper import wait_between


class Clicker:
    @staticmethod
    async def click_button(button):
        click_delay = random.uniform(70, 130)
        await wait_between(2000, 4000)
        await button.click(delay=click_delay / 1000)


class ImageFramer(Clicker):
    async def click_reload_button(self):
        reload_button = await self.image_frame.J("#recaptcha-reload-button")
        await self.click_button(reload_button)
