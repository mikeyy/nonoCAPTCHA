#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random
import signal
import sys

from async_timeout import timeout
from asyncio import TimeoutError, CancelledError

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings

signal.signal(signal.SIGINT, signal.SIG_DFL)


# Max browsers to open
threads = 1

sort_position = True
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


def shuffle(i):
    random.shuffle(i)
    return i


proxies = None


async def get_proxies():
    global proxies
    while True:
        protos = ["http://", "https://"]
        if any(p in proxy_src for p in protos):
            f = util.get_page
        else:
            f = util.load_file

        result = await f(proxy_src)
        proxies = iter(shuffle(result.strip().split("\n")))
        await asyncio.sleep(10 * 60)


def loop_proxies():
    asyncio.ensure_future(get_proxies(), loop=loop)


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

    if proxy_src:
        proxy = next(proxies)
    else:
        proxy = None

    client = Solver(
        settings["pageurl"], settings["sitekey"], options=options, proxy=proxy
    )

    answer = None
    try:
        async with timeout(180):
            answer = await client.start()
    except CancelledError:
        # Let's make sure Chrome closes after ungraceful exit
        if client.launcher:
            if not client.launcher.chromeClosed:
                await client.launcher.waitForChromeToClose()
        raise
    finally:
        if sort_position:
            used_positions.remove(this_position)
        if answer:
            return answer


async def main():
    if proxy_src:
        print("Proxies loading...")
        while proxies is None:
            await asyncio.sleep(1)

    tasks = [asyncio.ensure_future(work()) for i in range(threads)]
    completed, pending = await asyncio.wait(
        tasks, return_when=asyncio.FIRST_COMPLETED
    )
    count = 0
    while True:
        for task in completed:
            result = task.result()
            if result:
                count += 1
                print(f"{count}: {result}")
        pending.add(asyncio.ensure_future(work()))
        completed, pending = await asyncio.wait(
            pending, return_when=asyncio.FIRST_COMPLETED
        )


if sys.platform == "win32":
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
else:
    loop = asyncio.get_event_loop()

proxy_src = settings["proxy_source"]
if proxy_src:
    asyncio.ensure_future(get_proxies())

try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    raise
