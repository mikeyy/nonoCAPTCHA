from nonocaptcha import util


class GRIS(util.ImageFramer):
    def __init__(self, image_frame):
        self.image_frame = image_frame

    async def get_images(self):
        table = await self.image_frame.querySelector('table')
        rows = await table.querySelectorAll('tr')
        for row in rows:
            cells = await row.querySelectorAll('td')
            for cell in cells:
                yield cell

    async def is_solvable(self):
        name1 = await self.image_frame.querySelector('.rc-imageselect-desc')
        name2 = await self.image_frame.querySelector('.rc-imageselect-desc-no-canonical')

        handle = name1 if name1 else name2
        desc = await self.image_frame.evaluate('el => el.innerHTML', handle)
        return desc

    async def save_images(self):
        async for image in self.get_images():
            print(hash(image))
            image.screenshot({'path': f'pics/{hash(image)}.png'})
