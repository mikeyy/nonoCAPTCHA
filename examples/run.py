#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random
import sys

from async_timeout import timeout
from asyncio import CancelledError

from nonocaptcha import util, settings
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

# Max browsers to open
threads = 10
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
    def __init__(self, loop):
        self.proxies = ProxyDB()
        if proxy_source:
            asyncio.ensure_future(self.get_proxies(), loop=loop)

    async def get_proxies(self):
        while True:
            print("Proxies loading...")
            protos = ["http://", "https://"]
            if any(p in proxy_source for p in protos):
                f = util.get_page
            else:
                f = util.load_file

            result = await f(proxy_source)
            self.proxies.add(result.split('\n'))
            print("Proxies loaded.")
            await asyncio.sleep(10 * 60)

    async def work(self):
        args = ["--timeout 5"]
        if sort_position:
            this_position = next(
                x for x in positions if x not in used_positions
            )
            used_positions.append(this_position)
            args.extend(
                [
                    "--window-position=%s,%s" % this_position,
                    "--window-size=400,400",
                ]
            )
        options = {"ignoreHTTPSErrors": True, "args": args}
        proxy = await self.proxies.get() if proxy_source else None
        client = Solver(
            pageurl,
            sitekey,
            options=options,
            proxy=proxy
        )
        try:
            async with timeout(180):
                result = await client.start()
        except CancelledError:
            if client.launcher:
                if not client.launcher.chromeClosed:
                    await client.launcher.waitForChromeToClose()
        finally:
            if sort_position:
                used_positions.remove(this_position)

            if result:
                print(result)
                self.proxies.set_active(proxy, False)
                if result['status'] == "detected":
                    self.proxies.set_banned(proxy)
                else:
                    self.proxies.set_used(proxy)
                    if result['status'] == "success":
                        return result['code']

    async def main(self):
        if proxy_source:
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

loop.run_until_complete(Run(loop).main())
