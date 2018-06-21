#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utility functions."""

import aiohttp
import aiofiles
import pickle
from async_timeout import timeout as async_timeout
from concurrent.futures._base import TimeoutError

__all__ = ["save_file", "load_file", "get_page"]


async def save_file(file, data, binary=False):
    mode = "w" if not binary else "wb"
    async with aiofiles.open(file, mode=mode) as f:
        await f.write(data)


async def load_file(file):
    async with aiofiles.open(file, mode="r") as f:
        return await f.read()


async def get_page(url, proxy=None, binary=False, verify=False, timeout=300):
    if proxy:
        proxy = f"http://{proxy}"

    async with aiohttp.ClientSession() as session:
        try:
            async with async_timeout(timeout) as cm:
                async with session.get(
                    url, proxy=proxy, verify_ssl=verify
                ) as response:
                    if binary:
                        return await response.read()
                    return await response.text()
        except TimeoutError:
            return None


def serialize(obj, p):
    with open(p, 'wb') as f:
        pickle.dump(obj, f)


def deserialize(p):
    with open(p, 'rb') as f:
        return pickle.load(f)
