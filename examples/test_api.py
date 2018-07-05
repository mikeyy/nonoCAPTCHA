#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random
import time

from nonocaptcha import util, settings
from nonocaptcha.solver import Solver

count = 10
pageurl = settings["run"]["pageurl"]
sitekey = settings["run"]["sitekey"]

async def work():
    start = time.time()
    result = await util.get_page(
        f"http://localhost:5000/get?"
        f"pageurl={pageurl}&sitekey={sitekey}"
    )
    end = time.time()
    elapsed = end - start
    return (elapsed, result)


async def main():
    tasks = [asyncio.ensure_future(work()) for i in range(count)]

    futures = await asyncio.gather(*tasks)
    for (i, future) in zip(range(count), futures):
        print(i, future)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
