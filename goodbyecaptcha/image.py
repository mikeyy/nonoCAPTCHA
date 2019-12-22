#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
from http.server import BaseHTTPRequestHandler
from time import sleep

from PIL import Image

from goodbyecaptcha import package_dir
from goodbyecaptcha import util
from goodbyecaptcha.base import Base, settings
from goodbyecaptcha.exceptions import SafePassage
from goodbyecaptcha.predict import predict, is_marked

PICTURES = os.path.join(package_dir, settings['data']['pictures'])


class Handler(BaseHTTPRequestHandler):
    base_path = None

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        image_file = os.path.join(self.base_path, self.path.lstrip('/'))
        self.wfile.write(open(image_file, 'rb').read())


class SolveImage(Base):
    def __init__(self, page, image_frame, proxy, proxy_auth, proc_id):
        self.page = page
        self.image_frame = image_frame
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.proc_id = proc_id
        self.cur_image_path = None
        self.title = None
        self.pieces = None
        self.download = None
        self.loop = asyncio.get_event_loop()
        self.method = 'images'

    async def start(self):
        self.log('Solving Image ...')
        await self.set_title()
        image = await self.download_image()
        await self.create_folder(self.title, image)
        file_path = os.path.join(self.cur_image_path, f'{self.title}.jpg')
        await util.save_file(file_path, image, binary=True)  # Save Image
        self.pieces = await self.image_no()  # Detect Type Captcha (9 or 16)
        return file_path

    async def solve_by_image(self):
        while True:
            file_path = await self.start()  # Detect pieces and get images
            chooses = await self.choose(file_path)  # Choose images of the title
            await self.click_image(chooses)
            if self.pieces == 16:
                await self.click_verify()
                if not await self.is_next() and not await self.is_finish():
                    await self.click_reload_button()
            elif self.pieces == 9:
                if chooses:
                    if await self.is_one_selected():
                        await self.click_verify()
                        if not await self.is_next() and not await self.is_finish():
                            await self.click_reload_button()
                    else:
                        await self.cycle_selected(chooses)
                        await self.click_verify()
                        if not await self.is_next() and not await self.is_finish():
                            await self.click_reload_button()
                else:
                    await self.click_reload_button()
            if await self.is_finish():
                return {'status': 'success'}
            try:
                result = await self.check_detection(self.animation_timeout)
                return result
            except SafePassage:
                pass
            continue
        return {'status': '?'}

    async def cycle_selected(self, selected):
        while True:
            self.log('Get New Images')
            sleep(self.animation_timeout / 1000)
            images = await self.get_images_block(selected)
            new_selected = []
            i = 0
            for image_url in images:
                # Comprobate if is image change
                if images != self.download:
                    self.log('Download New Image # {0}/{1}'.format(i + 1, len(images)))
                    image = await util.get_page(
                        image_url, self.proxy, self.proxy_auth, binary=True
                    )
                    await self.create_folder(self.title, image)
                    file_path = os.path.join(self.cur_image_path, f'{self.title}.jpg')
                    # Save Image
                    await util.save_file(file_path, image, binary=True)

                    result = await predict(file_path)
                    self.log('result  #' + str(selected[i]) + ' ' + str(result))
                    if self.title == 'vehicles':
                        if 'car' in result or 'truck' in result:
                            new_selected.append(selected[i])
                    if self.title != 'vehicles' and self.title.replace('_', ' ') in result:
                        new_selected.append(selected[i])
                i += 1
            if new_selected:
                await self.click_image(new_selected)
            else:
                break

    async def choose(self, image_path):
        selected = []
        # Use Prediction Image
        if self.pieces == 9:
            # Cut Images
            image_obj = Image.open(image_path)
            util.split_image(image_obj, self.pieces, self.cur_image_path)
            # For pieces
            for i in range(self.pieces):
                # Predict everyone
                result = await predict(os.path.join(self.cur_image_path, f'{i}.jpg'))
                self.log('result #' + str(i) + ' ' + str(result))
                if self.title.replace('_', ' ') in result:
                    selected.append(i)
        else:
            result = await predict(image_path, self.title.replace('_', ' '))
            if result is not False:
                image_obj = Image.open(result)
                util.split_image(image_obj, self.pieces, self.cur_image_path)
                # Seleccionar Elementos
                for i in range(16):
                    if is_marked(f"{self.cur_image_path}/{i}.jpg"):
                        selected.append(i)
                os.remove(result)  # Clear tmp archive
        # Show Selected
        self.log('Selected: ' + str(selected))
        return selected

    async def get_images(self):
        table = await self.image_frame.querySelector('table')
        rows = await table.querySelectorAll('tr')
        for row in rows:
            cells = await row.querySelectorAll('td')
            for cell in cells:
                yield cell

    async def click_image(self, list_id):
        self.log('Clicking images ...')
        elements = await self.image_frame.querySelectorAll('.rc-imageselect-tile')
        for i in list_id:
            try:
                await self.click_button(elements[i])
            except Exception as ex:
                self.log(ex)

    async def click_verify(self):
        self.log('Verifying ...')
        element = await self.image_frame.querySelector('#recaptcha-verify-button')
        try:
            await self.click_button(element)
            sleep(self.animation_timeout / 1000)
        except Exception as ex:
            self.log(ex)
            raise Exception(ex)

    async def search_title(self, title):
        list_title = ('bus', 'car', 'bicycle', 'fire_hydrant', 'crosswalk',
                      'stair', 'bridge', 'traffic_light', 'vehicles',
                      'motorcycle', 'boat', 'chimneys')
        posible_titles = (
            ('autobuses', 'autobús', 'bus', 'buses'),
            ('automóviles', 'cars', 'car', 'coches', 'coche'),
            ('bicicletas', 'bicycles', 'bicycle', 'bici'),
            ('boca de incendios', 'boca_de_incendios', 'una_boca_de_incendios', 'fire_hydrant', 'fire_hydrants', 'a_fire_hydrant',
             'bocas_de_incendios'),
            ('cruces_peatonales', 'crosswalk', 'crosswalks', 'cross_walks', 'cross_walk', 'pasos_de_peatones'),
            ('escaleras', 'stair', 'stairs'),
            ('puentes', 'bridge', 'bridges'),
            ('semaforos', 'semaphore', 'semaphores', 'traffic_lights', 'traffic_light', 'semáforos'),
            ('vehículos', 'vehicles'),
            ('motocicletas', 'motocicleta', 'motorcycle', 'motorcycle'),
            ('boat', 'boats', 'barcos', 'barco'),
            ('chimeneas', 'chimneys', 'chimney', 'chimenea')
        )
        self.log(f'Searching title: {title}')
        i = 0
        for objects in posible_titles:
            if title in objects:
                self.log(f'Found title: {title} in {list_title[i]}')
                return list_title[i]
            i += 1
        self.log(f'No Found title: {title}')
        return title

    async def pictures_of(self):
        el = await self.get_description_element()
        of = await self.image_frame.evaluate(
            'el => el.firstElementChild.innerText', el
        )
        return str(of).replace(' ', '_')

    async def get_description_element(self):
        name1 = await self.image_frame.querySelector('.rc-imageselect-desc')
        name2 = await self.image_frame.querySelector(
            '.rc-imageselect-desc-no-canonical'
        )
        return name1 if name1 else name2

    async def create_folder(self, title, image):
        if not os.path.exists(PICTURES):
            os.mkdir(PICTURES)
        if not os.path.exists(os.path.join(PICTURES, f'{title}')):
            os.mkdir(os.path.join(PICTURES, f'{title}'))
        # Save Image
        self.cur_image_path = os.path.join(os.path.join(PICTURES, f'{title}'), f'{hash(image)}')
        if not os.path.exists(self.cur_image_path):
            os.mkdir(self.cur_image_path)

    async def get_image_url(self):
        image_url = (
            'document.getElementsByClassName("rc-image-tile-wrapper")[0].'
            'getElementsByTagName("img")[0].src'
        )
        return await self.image_frame.evaluate(image_url)

    async def image_no(self):
        self.log('image_n: ' + str(len([i async for i in self.get_images()])))
        return len([i async for i in self.get_images()])

    async def is_one_selected(self):
        comprobate = (
            'document.getElementsByClassName("rc-imageselect-tileselected").'
            'length === 0'
        )
        return not await self.image_frame.evaluate(comprobate)

    async def is_finish(self):
        try:
            result = await self.loop.create_task(
                self.check_detection(self.animation_timeout))
        except SafePassage:
            return False
        else:
            if result["status"] == "success":
                return True
        return False

    async def is_next(self):
        image_url = await self.get_image_url()
        return False if image_url == self.download else True

    async def download_image(self):
        self.log('Downloading Image ...')
        self.download = await self.get_image_url()
        return await util.get_page(
            self.download, self.proxy, self.proxy_auth, binary=True
        )

    async def get_images_block(self, images):
        images_url = []
        for element in images:
            image_url = (
                f'document.getElementsByClassName("rc-image-tile-wrapper")[{element}].'
                'getElementsByTagName("img")[0].src'
            )
            result = await self.image_frame.evaluate(image_url)
            images_url.append(result)
        return images_url

    async def set_title(self):
        title = await self.pictures_of()
        self.log(f'Image of {title}')
        self.title = await self.search_title(title)
