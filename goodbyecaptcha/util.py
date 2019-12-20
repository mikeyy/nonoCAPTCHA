#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Utility functions. """
import asyncio
import glob
import itertools
import os
import pickle
import random
import sys

import aiofiles
import requests
import urllib3
from bs4 import BeautifulSoup

__all__ = [
    'get_event_loop',
    "save_file",
    "load_file",
    "get_page",
    "get_random_proxy",
    "get_proxy",
    "serialize",
    "deserialize"]


def get_event_loop():
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()


async def save_file(file, data, binary=False):
    mode = "w" if not binary else "wb"
    async with aiofiles.open(file, mode=mode) as f:
        await f.write(data)


async def load_file(file, binary=False):
    mode = "r" if not binary else "rb"
    async with aiofiles.open(file, mode=mode) as f:
        return await f.read()


async def get_page_win(
        url,
        proxy=None,
        proxy_auth=None,
        binary=False,
        verify=False,
        timeout=300):
    proxies = None
    if proxy:
        if proxy_auth:
            proxy = proxy.replace("http://", "")
            username = proxy_auth['username']
            password = proxy_auth['password']
            proxies = {
                "http": f"http://{username}:{password}@{proxy}",
                "https": f"http://{username}:{password}@{proxy}"}
        else:
            proxies = {"http": proxy, "https": proxy}
    with requests.Session() as session:
        response = session.get(
            url,
            proxies=proxies,
            verify=verify,
            timeout=timeout)
        if binary:
            return response.content
        return response.text


async def get_page(
        url,
        proxy=None,
        proxy_auth=None,
        binary=False,
        verify=False,
        timeout=300):
    urllib3.disable_warnings()
    return await get_page_win(
        url, proxy, proxy_auth, binary, verify, timeout)


def serialize(obj, p):
    """Must be synchronous to prevent corrupting data"""
    with open(p, "wb") as f:
        pickle.dump(obj, f)


async def deserialize(p):
    data = await load_file(p, binary=True)
    return pickle.loads(data)


def split_image(image_obj, pieces, save_to):
    """Splits an image into constituent pictures of x"""
    width, height = image_obj.size
    row_length = 3 if pieces == 9 else 4
    interval = width // row_length
    for x, y in itertools.product(range(row_length), repeat=2):
        cropped = image_obj.crop((interval * x, interval * y,
                                  interval * (x + 1), interval * (y + 1)))
        cropped.save(os.path.join(save_to, f'{y * row_length + x}.jpg'))


def get_proxies():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = BeautifulSoup(response.text, "html.parser")
    proxies = list()
    for element in parser.find('table', {'id': 'proxylisttable'}).find_all('tr')[1:-1]:
        more = element.find_all('td')[:2]
        proxies.append(
            str(more[0]).replace('<td>', '').replace('</td>', '') + ':' + str(more[1]).replace('<td>', '').replace(
                '</td>', '').replace('https://', '').replace('http://', ''))
    return proxies


def get_proxy(proxys):
    result = random.choice(proxys)
    return result['ip'] + ':' + result['port']


def get_random_proxy():
    return random.choice(get_proxies())


def get_train_and_test(path, out):
    folders = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for folder in d:
            folders.append(os.path.join(r, folder))

    for directory in folders:
        file = directory.split('/')[-1:][0]
        print('Extract Train and Test of Directory:', file)
        # Percentage of images to be used for the test set
        percentage_test = 20
        # Create and/or truncate train.txt and test.txt
        file_train = open(os.path.join(out, 'data_train.txt'), 'a')
        file_test = open(os.path.join(out, 'data_test.txt'), 'a')
        # Populate train.txt and test.txt
        counter = 1
        index_test = round(100 / percentage_test)
        for pathAndFilename in glob.iglob(os.path.join(directory, "*.jpg")):
            title, ext = os.path.splitext(os.path.basename(pathAndFilename))
            if counter == index_test:
                counter = 1
                file_test.write(directory + "/" + title + '.jpg' + "\n")
            else:
                file_train.write(directory + "/" + title + '.jpg' + "\n")
                counter = counter + 1
