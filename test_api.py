#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import aiomisc
import asyncio
import random
import time

import util
from config import settings
from solver import Solver


async def work():
    async with sem:
        start = time.time()
        pageurl = settings["pageurl"]
        sitekey = settings["sitekey"]
        result = await util.get_page(
            f"http://localhost:5000/get?"
            f"pageurl={pageurl}&sitekey={sitekey}"
        )
        end = time.time()
        elapsed = end - start
        return (elapsed, result)


async def main():
    global sem

    tasks = []
    sem = asyncio.Semaphore(50)
    for i in range(count):
        task = asyncio.ensure_future(work())
        tasks.append(task)

    futures = await asyncio.gather(*tasks)
    for (i, future) in zip(range(count), futures):
        print(i, future)


count = 10
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
