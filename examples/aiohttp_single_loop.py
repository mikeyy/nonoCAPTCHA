#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Single loop example using executor to spawn tasks. A task will continue
to retry solving until it succeeds or times-out per the specified duration.
Default is 180 seconds (3 minutes). On shutdown cleanup will propagate,
hopefully closing left-over browsers and removing temporary profile folders.
"""

import asyncio
import shutil

from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRET_KEY = "CHANGEME"

proxies = ProxyDB(last_banned_timeout=45*60) # This is 45 minutes
proxy_source = None  # Can be URL or file location
proxy_username, proxy_password = (None, None)

parent_loop = asyncio.get_event_loop()
#  I'm not sure exactly if FastChildWatcher() is really any faster, requires
#  future research.
asyncio.set_child_watcher(asyncio.FastChildWatcher())
asyncio.get_child_watcher().attach_loop(parent_loop)

app = web.Application()

# Clear Chrome temporary profiles
dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)


#  Should be less crash prone since we use the main loop, only spawning the
#  task in a future within an executor. Maybe.
class TaskRerun(object):

    def __init__(self, coro, duration):
        self.coro = coro
        self.duration = duration
        self._executor = ThreadPoolExecutor()
        self._loop = asyncio.get_event_loop()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, exc_type, tb):
        self._executor.shutdown()
        return self

    async def start(self):
        def start():
            task = asyncio.run_coroutine_threadsafe(
                    self.seek(), self._loop)
            #  Emulate a timeout with call_later by calling task.cancel
            self._loop.call_soon_threadsafe(
                self._loop.call_later, self.duration, task.cancel)
            result = task.result()
            return result
        try:
            result = await self._loop.run_in_executor(self._executor, start)
        except Exception:
            result = None
        finally:
            return result

    async def seek(self):
        def callback(task):
            #  Consume Exception to satisfy event loop
            try:
                task.result()
            except Exception:
                pass
        while True:
            try:
                task = asyncio.wrap_future(
                    asyncio.run_coroutine_threadsafe(
                        self.coro(self._loop), self._loop))
                task.add_done_callback(callback)
                await task
                result = task.result()
                if result is not None:
                    return result
            except asyncio.CancelledError:
                break
            except Exception:
                pass


async def work(pageurl, sitekey, loop):
    proxy = proxies.get()
    proxy_auth = None
    if proxy_username and proxy_password:
        proxy_auth = {"username": proxy_username,
                      "password": proxy_password}
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
    client = Solver(
        pageurl,
        sitekey,
        loop=loop,
        options=options,
        proxy=proxy,
        proxy_auth=proxy_auth
    )
    result = await client.start()
    if result:
        if result['status'] == "detected":
            loop.call_soon_threadsafe(proxies.set_banned, proxy)
        else:
            if result['status'] == "success":
                return result['code']


async def get_solution(request):
    params = request.rel_url.query
    pageurl = params.get("pageurl")
    sitekey = params.get("sitekey")
    secret_key = params.get("secret_key")
    if not pageurl or not sitekey or not secret_key:
        response = {"error": "invalid request"}
    else:
        if secret_key != SECRET_KEY:
            response = {"error": "unauthorized attempt logged"}
        else:
            if pageurl and sitekey:
                coro = partial(work, pageurl, sitekey)
                async with TaskRerun(coro, duration=180) as t:
                    result = await t.start()
                if result:
                    response = {"solution": result}
                else:
                    response = {"error": "worker timed-out"}
    return web.json_response(response)


async def load_proxies():
    print('Loading proxies')
    while 1:
        protos = ["http://", "https://"]
        if proxy_source is None:
            return
        if any(p in proxy_source for p in protos):
            f = util.get_page
        else:
            f = util.load_file

        try:
            result = await f(proxy_source)
        except Exception:
            continue
        else:
            proxies.add(result.split('\n'))
            print('Proxies loaded')
            await asyncio.sleep(10 * 60)


async def start_background_tasks(app):
    app["dispatch"] = app.loop.create_task(load_proxies())


async def cleanup_background_tasks(app):
    app["dispatch"].cancel()
    await app["dispatch"]


app.router.add_get("/", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
