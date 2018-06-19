#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utility functions."""

import aiohttp
import asyncio
import aiofiles
import functools
import logging
from async_timeout import timeout as async_timeout

__all__ = ["save_file", "load_file", "get_page"]


async def save_file(file, data, binary=False):
    mode = "w" if not binary else "wb"
    async with aiofiles.open(file, mode=mode) as f:
        await f.write(data)


async def load_file(file):
    async with aiofiles.open(file, mode="r") as f:
        return await f.read()


async def get_page(url, proxy=None, binary=False, verify=False, timeout=60):
    if proxy:
        proxy = f"http://{proxy}"

    async with aiohttp.ClientSession() as session:
        async with async_timeout(timeout):
            async with session.get(
                url, proxy=proxy, verify_ssl=verify
            ) as response:
                if binary:
                    return await response.read()
                return await response.text()


def throw_away_exceptions(f):
    """Decorator that returns None if an exception occured and logs the exception. Use with cation."""
    @functools.wraps(f)
    async def inner(*args, **kwargs):
        try:
            if asyncio.iscoroutinefunction(f):
                return await f(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        except BaseException as e:
            logging.debug(f'{f.__name__} encountered an error: {e} {type(e)}')
    return inner
