#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Example run functions."""

import asyncio
import random
import sys

from async_timeout import timeout

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

threads = 1  # Max browsers to open
sort_position = False

pageurl = "https://www.google.com/recaptcha/api2/demo"
sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

proxy_source = None  # Can be URL or file location
proxy_username, proxy_password = (None, None)


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
    proxies_loading = True

    def __init__(self, loop):
        self.proxies = ProxyDB(last_banned_timeout=45*60)
        if proxy_source:
            asyncio.ensure_future(self.get_proxies(), loop=loop)

    async def get_proxies(self):
        while True:
            self.proxies_loading = True
            print("Proxies loading...")
            protos = ["http://", "https://"]
            if any(p in proxy_source for p in protos):
                f = util.get_page
            else:
                f = util.load_file

            result = await f(proxy_source)
            self.proxies.add(result.split('\n'))
            self.proxies_loading = False
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
        options = {
            "ignoreHTTPSErrors": True,
            "args": args
        }
        proxy = self.proxies.get() if proxy_source else None
        proxy_auth = None
        if proxy_username and proxy_password:
            proxy_auth = {"username": proxy_username,
                          "password": proxy_password}
        client = Solver(
            pageurl,
            sitekey,
            options=options,
            proxy=proxy,
            proxy_auth=proxy_auth
        )
        result = None
        try:
            async with timeout(180):
                result = await client.start()
        finally:
            if sort_position:
                used_positions.remove(this_position)

            if result:
                self.proxies.set_active(proxy, False)
                if result['status'] == "detected":
                    self.proxies.set_banned(proxy)
                else:
                    if result['status'] == "success":
                        return result['code']

    async def main(self):
        if proxy_source:
            while not self.proxies_loading:
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

r = Run(loop)
loop.run_until_complete(r.main())
