#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random

import util
from config import settings
from solver import Solver

# Browsers to open (and keep running with random proxies)
count = 4
loop = asyncio.get_event_loop()


def get_proxies():
    src = settings["proxy_source"]
    protos = ["http://", "https://"]
    if any(p in src for p in protos):
        f = util.get_page
    else:
        f = util.load_file

    future = asyncio.ensure_future(f(src))
    loop.run_until_complete(future)
    result = future.result()
    return result.strip().split("\n")


async def work():
    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, 
               "args": ["--timeout 5"]
    }

    proxy = random.choice(proxies)
    client = Solver(
        settings["pageurl"],
        settings["sitekey"],
        options=options,
        proxy=proxy
    )

    if client.debug:
        print(f'Starting solver with proxy {proxy}')

    answer = await client.start()
    return answer


async def main():
    global count

    active_tasks = set()
    while True:
        tasks = active_tasks | set(asyncio.ensure_future(work()) for i in range(count))
        futures = await asyncio.wait(tasks, return_when='FIRST_COMPLETED',
                                     timeout=sum(settings['wait_timeout'].values()))
        completed = futures[0]
        for i, future in enumerate(completed, 1):
            print(i, future)
        active_tasks = set(t for t in tasks if not t.done())
        count = len(tasks - active_tasks)  # spawns `count` new tasks


proxies = get_proxies()
print(len(proxies), "Loaded")

loop.run_until_complete(main())
