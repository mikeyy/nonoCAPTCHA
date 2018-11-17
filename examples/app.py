#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Threaded example using executor to create a new event loop for running a
task. Each task will continue to retry solving until it succeeds or times-out
per the specified duration. Default is 180 seconds (3 minutes). On shutdown
cleanup will propagate, hopefully closing left-over browsers and removing
temporary profile folders.
"""

import asyncio
import shutil
import sys

from aiohttp import web
from async_timeout import timeout
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from threading import RLock

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRET_KEY = "CHANGEME"
BANNED_TIMEOUT = 45*60  # 45 minutes
SOLVE_DURATION = 3*60  # 3 minutes

proxies = ProxyDB(last_banned_timeout=BANNED_TIMEOUT)
proxy_source = None  # Can be URL or file location
proxy_username, proxy_password = (None, None)

if sys.platform == "win32":
    parent_loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(parent_loop)
else:
    parent_loop = asyncio.get_event_loop()
    asyncio.get_child_watcher().attach_loop(parent_loop)

app = web.Application()

# Clear Chrome temporary profiles
dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)


# Bugs are to be expected, despite my efforts. Apparently, event loops paired
# with threads is nothing short of a hassle.
class TaskRerun(object):

    def __init__(self, coro, duration):
        self.coro = coro
        self.duration = duration
        self._executor = ThreadPoolExecutor()
        self._lock = RLock()

    async def __aenter__(self):
        asyncio.ensure_future(
            asyncio.wrap_future(
                self._executor.submit(self.prepare_loop)))
        return self

    async def __aexit__(self, exc, exc_type, tb):
        asyncio.ensure_future(
            asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(self.cleanup(), self._loop)))
        return self

    def prepare_loop(self):
        #  Surrounding the context around run_forever never releases the lock!
        with self._lock:
            if sys.platform == "win32":
                self._loop = asyncio.ProactorEventLoop()
            else:
                self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def start(self):
        with self._lock:
            # Blocking occurs unless wrapped in an asyncio.Future object
            task = asyncio.wrap_future(
                        asyncio.run_coroutine_threadsafe(
                            self.seek(), self._loop))
            try:
                # Wait for the Task to complete or Timeout
                async with timeout(self.duration):
                    await task
                result = task.result()
            except Exception:
                result = None
            finally:
                return result

    async def seek(self):
        def callback(task):
            # Consume Exception to satisfy event loop
            try:
                task.result()
            except Exception:
                pass
        while True:
            try:
                # Deadlock occurs unless wrapped in an asyncio.Future object.
                # We could also use AbstractEventLoop.create_task here.
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
            # We don't want to leave the loop unless result or cancelled
            except Exception:
                pass

    async def cleanup(self):
        # A maximum recursion depth occurs when current task gets called for
        # cancellation from gather.
        pending = tuple(
            task for task in asyncio.Task.all_tasks(loop=self._loop)
            if task is not asyncio.Task.current_task())
        gathered = asyncio.gather(
            *pending, loop=self._loop, return_exceptions=True)
        gathered.cancel()
        await gathered
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.executor.shutdown()


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
                async with TaskRerun(coro, duration=SOLVE_DURATION) as t:
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
