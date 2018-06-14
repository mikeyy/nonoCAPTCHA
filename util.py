#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Utility functions."""

import backoff
import aiohttp
import aiofiles

__all__ = ["save_file", "load_file", "get_page"]

HTTP_MAX_RETRIES = 3


async def save_file(file, data, binary=False):
    mode = "w" if not binary else "wb"
    async with aiofiles.open(file, mode=mode) as f:
        await f.write(data)


async def load_file(file):
    async with aiofiles.open(file, mode="r") as f:
        return await f.read()


#@backoff.on_exception(
#    backoff.expo, aiohttp.ClientError, max_tries=HTTP_MAX_RETRIES
#)
async def get_page(url, proxy=None, binary=False, verify=False):
    if proxy:
        proxy = f"http://{proxy}"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, proxy=proxy, verify_ssl=verify
        ) as response:
            if binary:
                return await response.read()
            return await response.text()
