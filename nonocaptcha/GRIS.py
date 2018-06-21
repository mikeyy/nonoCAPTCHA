from quart import Quart, Response, request

from config import settings
from nonocaptcha import util
from nonocaptcha.base import ImageFramer


class GRIS(ImageFramer):
    url = 'https://www.google.com/searchbyimage?site=search&sa=X&image_url='

    def __init__(self, image_frame, proxy, log):
        self.image_frame = image_frame
        self.proxy = proxy
        self.log = log

    async def get_images(self):
        table = await self.image_frame.querySelector('table')
        rows = await table.querySelectorAll('tr')
        for row in rows:
            cells = await row.querySelectorAll('td')
            for cell in cells:
                yield cell

    async def is_solvable(self):
        el = await self.get_description()
        desc = await self.image_frame.evaluate('el => el.innerText', el)
        return 'images' in desc

    async def pictures_of(self):
        el = await self.get_description()
        return await self.image_frame.evaluate('el => el.firstElementChild.innerText', el)

    async def get_description(self):
        name1 = await self.image_frame.querySelector('.rc-imageselect-desc')
        name2 = await self.image_frame.querySelector('.rc-imageselect-desc-no-canonical')
        return name1 if name1 else name2

    async def save_images(self):
        """Saves images to a websever to send to GRIS"""
        # https://github.com/GoogleChrome/puppeteer/issues/2729
        async for image in self.get_images():
            await image.screenshot({'path': f'{settings["data_files"]["pics"]}/{hash(image)}.png'})  # crashes on mac..
