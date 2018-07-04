#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random
import signal
import sys

from async_timeout import timeout
from asyncio import TimeoutError, CancelledError

from nonocaptcha import settings
from nonocaptcha import util
from nonocaptcha.solver import Solver

signal.signal(signal.SIGINT, signal.SIG_DFL)


# Max browsers to open
threads = 1
sort_position = False
pageurl = settings["run"]["pageurl"]
sitekey = settings["run"]["sitekey"]
proxy_source = settings["proxy"]["source"]


def shuffle(i):
    random.shuffle(i)
    return i


if sort_position:
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


class Run(object):
    proxies = None
    def __init__(self, loop):
        if proxy_source:
            asyncio.ensure_future(self.get_proxies(), loop=loop)

    async def get_proxies(self):
        while True:
            protos = ["http://", "https://"]
            if any(p in proxy_source for p in protos):
                f = util.get_page
            else:
                f = util.load_file
    
            result = await f(proxy_source)
            self.proxies = iter(shuffle(result.strip().split("\n")))
            await asyncio.sleep(10 * 60)

    async def work(self):
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
        proxy = next(self.proxies) if proxy_source else None
        client = Solver(
            pageurl,
            sitekey,
            options=options,
            proxy=proxy
        )
        answer = None
        try:
            async with timeout(180):
                answer = await client.start()
        except CancelledError:
            if client.launcher:
                if not client.launcher.chromeClosed:
                    await client.launcher.waitForChromeToClose()
            raise
        else:
            if sort_position:
                used_positions.remove(this_position)
            if answer:
                return answer

    async def main(self):
        if proxy_source:
            print("Proxies loading...")
            while self.proxies is None:
                await asyncio.sleep(1)
    
        tasks = [asyncio.ensure_future(self.work()) for i in range(threads)]
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
            pending.add(asyncio.ensure_future(self.work()))
            completed, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )

if sys.platform == "win32":
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
else:
    loop = asyncio.get_event_loop()
        
try:
    loop.run_until_complete(Run(loop).main())
except KeyboardInterrupt:
    raise
