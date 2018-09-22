#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" ***IN TESTING*** """

import os
import asyncio
import threading
from PIL import Image
from operator import itemgetter
from concurrent.futures import ProcessPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler

from nonocaptcha import util
from nonocaptcha.base import Base, settings
from nonocaptcha import package_dir

import ipgetter

PICTURES = os.path.join(package_dir, settings['data']['pictures'])
EXECUTOR = ProcessPoolExecutor(1)  # not to be confused with Exeggutor


class Handler(BaseHTTPRequestHandler):
    base_path = None

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        image_file = os.path.join(self.base_path, self.path.lstrip('/'))
        self.wfile.write(open(image_file, 'rb').read())


class SolveImage(Base):
    url = 'https://www.google.com/searchbyimage?site=search&sa=X&image_url='
    ip_address = f'http://{ipgetter.myip()}'
    banned_titles = [
        'fire hydrant',
        'bus',
    ]

    def __init__(self, browser, image_frame, proxy, proxy_auth, proc_id):
        self.browser = browser
        self.image_frame = image_frame
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.proc_id = proc_id
        self.cur_image_path = None
        self.title = None
        self.pieces = None
        self.word_vectors_future = EXECUTOR.submit(util.init_word_similarity)
        self.word_vectors_obj = None

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
        of = of.lstrip('a ')
        of = 'bus' if of == 'buses' else of
        of = of.split(' or ')[0] if ' or ' in of else of
        return of.rstrip('s') if of[-2] not in 'saiou' else of

    async def get_description_element(self):
        name1 = await self.image_frame.querySelector('.rc-imageselect-desc')
        name2 = await self.image_frame.querySelector(
            '.rc-imageselect-desc-no-canonical'
        )
        return name1 if name1 else name2

    async def cycle_to_solvable(self):
        while True:
            self.title = await self.pictures_of()
            self.pieces = await self.image_no()
            if self.title.lower() not in self.banned_titles and \
                    self.pieces == 9 and await self.is_solvable():
                break
            await self.click_reload_button()

    async def solve_by_image(self):
        await self.cycle_to_solvable()
        print(f'Image of {self.title}')
        image = await self.download_image()
        self.cur_image_path = os.path.join(PICTURES, f'{hash(image)}')
        os.mkdir(self.cur_image_path)
        file_path = os.path.join(self.cur_image_path, f'{self.title}.jpg')
        await util.save_file(file_path, image, binary=True)
        image_obj = Image.open(file_path)
        util.split_image(image_obj, self.pieces, self.cur_image_path)
        self.start_app()
        queries = [self.reverse_image_search(i) for i in range(self.pieces)]
        results = await asyncio.gather(*queries, return_exceptions=True)
        print(results)
        pics_to_click = sorted((r for r in results if isinstance(r, tuple)),
                               key=itemgetter(1), reverse=True)[:3]  # select 3
        print(pics_to_click)
        await self.click_images([i[0] for i in pics_to_click])
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
            best_guess_of = best_guess.split(':')[1].lstrip()
        else:
            best_guess_of = ''
        print(image_no, best_guess_of)
        await asyncio.sleep(10)
        await page.close()
        if not self.word_vectors_future.done():
            self.log('Waiting for word vectors to load...')
        self.word_vectors_obj = self.word_vectors_future.result()  # blocks
        return image_no, self.compare(best_guess_of)

    async def click_images(self, indexes):
        image_elements = [im async for im in self.get_images()]
        for i in indexes:
            image = image_elements[i]
            await self.click_button(image)

    def compare(self, guess):
        """Returns True if our guess was more similar to the title than it is
           similar to the other keys that google offers. Similarity takes two
           words, does some magic, and returns a float"""
        if guess == '':
            return -1
        return max(self.word_vectors_obj.similarity(self.title, w)
                   for w in guess.split() if w in self.word_vectors_obj)

    def start_app(self):
        Handler.base_path = self.cur_image_path
        httpd = HTTPServer(('0.0.0.0', 8080), Handler)
        threading.Thread(target=httpd.serve_forever).start()
