#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random

import util
from config import settings
from solver import Solver

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


# Max browsers to open
threads = 1

sort_position = False
if sort_position:
    """Use only if you know what you are doing, haven't yet automated avialable
    screen space!
    """
    screen_width, screen_height = (1400, 1050)
    threads = int(1 + screen_width / 400 + 1 + screen_height / 400)

    position_x = 20
    position_y = 20

    positions = []
    used_positions = []

    positions.append((position_x, position_y))
    for i in range(threads):
        position_x += 400
        if position_x > screen_width:
            position_y += 400
            if position_y > screen_height:
                position_y = 20
            position_x = 20
        positions.append((position_x, position_y))


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

    args = ["--timeout 5"]
    if sort_position:
        this_position = next(x for x in positions if x not in used_positions)
        used_positions.append(this_position)
        args.extend(
            [
                "--window-position=%s,%s" % this_position,
                "--window-size=400,400",
            ]
        )

    options = {"ignoreHTTPSErrors": True, "args": args}

    proxy = random.choice(proxies)
    client = Solver(
        settings["pageurl"], settings["sitekey"], options=options, proxy=proxy
    )

    answer = await client.start()

    if sort_position:
        used_positions.remove(this_position)

    return answer


async def main():
    tasks = [asyncio.ensure_future(work()) for i in range(threads)]
    completed, pending = await asyncio.wait(
        tasks, return_when=asyncio.FIRST_COMPLETED
    )
    while 1:
        for task in completed:
            result = task.result()
            if result:
                print(result)
        new_task = [asyncio.ensure_future(work())]
        completed, pending = await asyncio.wait(
            set(new_task) | pending, return_when=asyncio.FIRST_COMPLETED
        )


loop = asyncio.get_event_loop()

proxies = get_proxies()
print(len(proxies), "Loaded")

loop.run_until_complete(main())
