#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Utility functions. """
import asyncio
import glob
import itertools
import pickle
import random
from math import sqrt

import aiofiles
import certifi
import requests
from bs4 import BeautifulSoup
from pyppeteer.chromium_downloader import *

__all__ = [
    'get_event_loop',
    "save_file",
    "load_file",
    "get_page",
    "get_random_proxy",
    "get_proxy",
    "serialize",
    "deserialize",
    "patch_pyppeteer"
]

NO_PROGRESS_BAR = os.environ.get('PYPPETEER_NO_PROGRESS_BAR', '')
if NO_PROGRESS_BAR.lower() in ('1', 'true'):
    NO_PROGRESS_BAR = True  # type: ignore

win_postf = "win" if int(REVISION) > 591479 else "win32"
downloadURLs.update({
    'win32': f'{BASE_URL}/Win/{REVISION}/chrome-{win_postf}.zip',
    'win64': f'{BASE_URL}/Win_x64/{REVISION}/chrome-{win_postf}.zip',
})
chromiumExecutable.update({
    'win32': DOWNLOADS_FOLDER / REVISION / f'chrome-{win_postf}' / 'chrome.exe',
    'win64': DOWNLOADS_FOLDER / REVISION / f'chrome-{win_postf}' / 'chrome.exe',
})


def get_event_loop():
    """Get loop of asyncio"""
    if sys.platform == "win32":
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()


async def save_file(file, data, binary=False):
    """Save data on file"""
    mode = "w" if not binary else "wb"
    async with aiofiles.open(file, mode=mode) as f:
        await f.write(data)


async def load_file(file, binary=False):
    """Load data on file"""
    mode = "r" if not binary else "rb"
    async with aiofiles.open(file, mode=mode) as f:
        return await f.read()


async def get_page(url, proxy=None, proxy_auth=None, binary=False, verify=False, timeout=300):
    """Get data of the page (File binary of Response text)"""
    urllib3.disable_warnings()
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
    retry = 3  # Retry 3 times
    while retry > 0:
        try:
            with requests.Session() as session:
                response = session.get(url, proxies=proxies, verify=verify, timeout=timeout)
                if binary:
                    return response.content
                return response.text
        except requests.exceptions.ConnectionError:
            retry -= 1


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
    row_length = int(sqrt(pieces))
    interval = width // row_length
    for x, y in itertools.product(range(row_length), repeat=2):
        cropped = image_obj.crop((interval * x, interval * y, interval * (x + 1), interval * (y + 1)))
        cropped.save(os.path.join(save_to, f'{y * row_length + x}.jpg'))


def get_proxies():
    """Get free proxy list of https://free-proxy-list.net/"""
    parser = BeautifulSoup(get_page('https://free-proxy-list.net/'), "html.parser")
    proxies = list()
    for element in parser.find('table', {'id': 'proxylisttable'}).find_all('tr')[1:-1]:
        more = element.find_all('td')[:2]
        proxies.append(
            str(more[0]).replace('<td>', '').replace('</td>', '') + ':' + str(more[1]).replace('<td>', '').replace(
                '</td>', '').replace('https://', '').replace('http://', ''))
    return proxies


def get_proxy(proxys):
    """Select one proxy list"""
    result = random.choice(proxys)
    return result['ip'] + ':' + result['port']


def get_random_proxy():
    """Get random one proxy list"""
    return random.choice(get_proxies())


def download_zip(url: str) -> BytesIO:
    """Download data from url."""
    logger.warning('start patched secure https chromium download.\n'
                   'Download may take a few minutes.')

    with urllib3.PoolManager(cert_reqs='CERT_REQUIRED',
                             ca_certs=certifi.where()) as https:
        # Get data from url.
        # set preload_content=False means using stream later.
        data = https.request('GET', url, preload_content=False)

        try:
            total_length = int(data.headers['content-length'])
        except (KeyError, ValueError, AttributeError):
            total_length = 0

        process_bar = tqdm(
            total=total_length,
            file=os.devnull if NO_PROGRESS_BAR else None,
        )

        # 10 * 1024
        _data = BytesIO()
        for chunk in data.stream(10240):
            _data.write(chunk)
            process_bar.update(len(chunk))
        process_bar.close()

    logger.warning('\nchromium download done.')
    return _data


def patch_pyppeteer():
    """Patch pyppeteer of InvalidStateError and SSLError Chrome download"""
    import pyppeteer.chromium_downloader
    import pyppeteer.connection

    pyppeteer.chromium_downloader.download_zip = download_zip
    _connect = pyppeteer.connection.websockets.client.connect

    def connect(*args, ping_interval=None, ping_timeout=None, **kwargs):
        return _connect(*args, ping_interval=ping_interval,
                        ping_timeout=ping_timeout, **kwargs)

    pyppeteer.connection.websockets.client.connect = connect


def get_train_and_test(path, out):
    """Create train and test directories to YoloV3"""
    folders = []
    for r, d, f in os.walk(path):  # r=root, d=directories, f = files
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
