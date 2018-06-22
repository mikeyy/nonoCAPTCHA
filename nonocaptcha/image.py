#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" ***IN TESTING*** """

class SolveImage(object):
    def __init__(self, page, proxy):
        self.page = page
        self.proxy = proxy
        self = super().__init__()

    async def solve_by_image(self):
        """Go through procedures to solve image"""
        
        title = await self.get_image_title()
        image_url = await self.get_image_url()
        
        return title

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
        image_url_element = (
            'document.getElementsByClassName("rc-image-tile-wrapper")[0].'
            'getElementsByTagName("img")[0].src'
        )

        return await self.image_frame.evaluate(f"{image_url_element}")