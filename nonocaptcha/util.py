#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utility functions."""

import aiohttp
import aiofiles
import pickle
from async_timeout import timeout as async_timeout
# from concurrent.futures._base import TimeoutError

__all__ = ["save_file", "load_file", "get_page"]


async def save_file(file, data, binary=False):
    mode = "w" if not binary else "wb"
    async with aiofiles.open(file, mode=mode) as f:
        await f.write(data)


async def load_file(file, binary=False):
    mode = "r" if not binary else "rb"
    async with aiofiles.open(file, mode=mode) as f:
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
        except: 
            return None


def serialize(obj, p):
    save_file(p, pickle.dump(obj, f), binary=True)


def deserialize(p):
    data = load_file(p, binary=True)
    return pickle.load(data)
