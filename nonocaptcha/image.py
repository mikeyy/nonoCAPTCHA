#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" ***IN TESTING*** """

from nonocaptcha.base import Base

import asyncio


class SolveImage(Base):
    url = 'https://www.google.com/searchbyimage?site=search&sa=X&image_url='

    def __init__(self, page, proxy, proc_id):
        self.page = page
        self.proxy = proxy
        self.proc_id = proc_id

    async def get_images(self):
        table = await self.image_frame.querySelector('table')
        rows = await table.querySelectorAll('tr')
        for row in rows:
            cells = await row.querySelectorAll('td')
            for cell in cells:
                yield cell

    async def is_solvable(self):
        el = await self.get_description_element()
        desc = await self.image_frame.evaluate('el => el.innerText', el)
        return 'images' in desc

    async def pictures_of(self):
        el = await self.get_description_element()
        return await self.image_frame.evaluate(
            'el => el.firstElementChild.innerText', el
        )

    async def get_description_element(self):
        name1 = await self.image_frame.querySelector('.rc-imageselect-desc')
        name2 = await self.image_frame.querySelector(
            '.rc-imageselect-desc-no-canonical'
        )
        return name1 if name1 else name2

    async def solve_by_image(self):
        while not await self.is_solvable():
            await self.click_reload_button()
        print(await self.pictures_of())
        print(await self.get_image_url())
        await asyncio.sleep(1)
        await self.get_image_dimensions()
        asyncio.sleep(10)

    async def get_image_title(self):
        """Something, something... something"""

        image_title_element = (
            'document.getElementsByClassName("rc-imageselect-desc")[0]'
        )

        if await self.image_frame.evaluate(
            f"typeof {image_title_element} === 'undefined'"
        ):
            image_title_element = (
                'document.getElementsByClassName("rc-imageselect-desc-no-'
                'canonical")[0]'
            )

        title = await self.image_frame.evaluate(
            f"{image_title_element}.innerText"
            f".replace( /.*\\n(.*)\\n.*/,'$1');"
        )
        return str(title).strip()

    async def get_image_url(self):
        image_url = (
            'document.getElementsByClassName("rc-image-tile-wrapper")[0].'
            'getElementsByTagName("img")[0].src'
        )
        return await self.image_frame.evaluate(image_url)

    async def get_image_dimensions(self):
        async for el in self.get_images():
            dimensions = await self.image_frame.evaluate(
                'el => el.firstElementChild.firstElementChild.style', el
            )
            print(dimensions)

    async def download_image(self):
        """work in progress"""
        # image_url = await self.get_image_url()
