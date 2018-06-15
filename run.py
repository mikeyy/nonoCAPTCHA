#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random
import time

import util
from config import settings
from solver import Solver


def get_proxies():
    src = settings["proxy_source"]
    protos = ["http://", "https://"]
    if any(p in src for p in protos):
        f = util.get_page
    else:
        f = util.load_file

    future = asyncio.ensure_future(f(settings["proxy_source"]))
    asyncio.get_event_loop().run_until_complete(future)
    result = future.result()
    return result.strip().split("\n")


async def work():
    options = {"headless": settings["headless"], "ignoreHTTPSErrors": True}

    proxy = random.choice(proxies)
    client = Solver(
        settings["pageurl"],
        settings["sitekey"],
        options=options,
        proxy=proxy,
        # proxy_auth=auth_details(),
    )

    print(f"Solving with proxy {proxy}")

    start = time.time()
    answer = await client.start()
    end = time.time()
    elapsed = end - start
    return (elapsed, answer)


async def main():
    global sem

    tasks = []
    for i in range(count):
        task = asyncio.ensure_future(work())
        tasks.append(task)

    futures = await asyncio.gather(*tasks)
    for (i, future) in zip(range(count), futures):
        print(i, future)


proxies = get_proxies()
print(len(proxies), "Loaded")

count = 1

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
