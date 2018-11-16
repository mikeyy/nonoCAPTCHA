#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" ***IN TESTING*** """

import os
import asyncio
import threading
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler

from nonocaptcha import util
from nonocaptcha.base import Base, settings
from nonocaptcha import package_dir

PICTURES = os.path.join(package_dir, settings['data']['pictures'])


class Handler(BaseHTTPRequestHandler):
    base_path = None

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        image_file = os.path.join(self.base_path, self.path.lstrip('/'))
        self.wfile.write(open(image_file, 'rb').read())


class SolveImage(Base):
    url = 'https://www.google.com/searchbyimage?site=search&sa=X&image_url='
    ip_address = 'http://91.121.226.109'

    def __init__(self, browser, image_frame, proxy, proxy_auth, proc_id):
        self.browser = browser
        self.image_frame = image_frame
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.proc_id = proc_id
        self.cur_image_path = None
        self.title = None
        self.pieces = None

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
        of = await self.image_frame.evaluate(
            'el => el.firstElementChild.innerText', el
        )
        return of.lstrip('a ')

    async def get_description_element(self):
        name1 = await self.image_frame.querySelector('.rc-imageselect-desc')
        name2 = await self.image_frame.querySelector(
            '.rc-imageselect-desc-no-canonical'
        )
        return name1 if name1 else name2

    async def cycle_to_solvable(self):
        while not await self.is_solvable() or await self.image_no() != 9:
            await self.click_reload_button()

    async def solve_by_image(self):
        await self.cycle_to_solvable()
        title = await self.pictures_of()
        pieces = 9  # TODO: crop other sizes
        image = await self.download_image()
        self.title = title
        print(f'Image of {title}')
        self.pieces = pieces
        os.mkdir(PICTURES)
        self.cur_image_path = os.path.join(PICTURES, f'{hash(image)}')
        os.mkdir(self.cur_image_path)
        file_path = os.path.join(self.cur_image_path, f'{title}.jpg')
        await util.save_file(file_path, image, binary=True)
        image_obj = Image.open(file_path)
        util.split_image(image_obj, pieces, self.cur_image_path)
        self.start_app()
        queries = [self.reverse_image_search(i) for i in range(pieces)]
        results = await asyncio.gather(*queries, return_exceptions=True)
        for r in results:
            if isinstance(r, tuple) and r[1] is True:
                pass
                # TODO: return a list of numbers corresponding to image index

        return {'status': '?'}

    async def get_image_url(self):
        image_url = (
            'document.getElementsByClassName("rc-image-tile-wrapper")[0].'
            'getElementsByTagName("img")[0].src'
        )
        return await self.image_frame.evaluate(image_url)

    async def image_no(self):
        return len([i async for i in self.get_images()])

    async def download_image(self):
        image_url = await self.get_image_url()
        return await util.get_page(
            image_url, self.proxy, self.proxy_auth, binary=True
        )

    async def reverse_image_search(self, image_no):
        image_path = f'{self.ip_address}:8080/{image_no}.jpg'
        url = self.url + image_path
        page = await self.browser.newPage()
        await page.goto(url)
        card = await page.querySelector('div.card-section')
        if card:
            best_guess = await page.evaluate('el => el.children[1].innerText',
                                             card)
            print(image_no, best_guess)
        else:
            best_guess = ''
        await asyncio.sleep(100)
        await page.close()
        return self.title in best_guess

    def start_app(self):
        Handler.base_path = self.cur_image_path
        httpd = HTTPServer(('0.0.0.0', 8080), Handler)
        threading.Thread(target=httpd.serve_forever).start()
