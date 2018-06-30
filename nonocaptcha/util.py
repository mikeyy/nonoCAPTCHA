#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utility functions."""

import aiohttp
import aiofiles
import asyncio
import pickle
from async_timeout import timeout as async_timeout
from functools import partial, wraps


__all__ = [
    "save_file",
    "load_file",
    "get_page",
    "threaded",
    "serialize",
    "deserialize"
]


def threaded(func):
    @wraps(func)
    async def wrap(*args, **kwargs):
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(
            None, partial(func, *args, **kwargs)
        )

    return wrap


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
        except BaseException as e:
            session.close()
            raise BaseException(f'An error occured in get_page: {e}')


def serialize(obj, p):
    """Must be synchronous to prevent corrupting data"""
    with open(p, 'wb') as f:
        pickle.dump(obj, f)


async def deserialize(p):
    data = await load_file(p, binary=True)
    return pickle.loads(data)
