import asyncio
import signal
import shutil
import sys

from aiohttp import web
from async_timeout import timeout
from asyncio import CancelledError, IncompleteReadError
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial, wraps
from pathlib import Path
from threading import Thread

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRET_KEY = "CHANGEME"

proxy_source = None  # Can be URL or file location
proxies = ProxyDB(last_banned_timeout=45*60)

pool = ThreadPoolExecutor()
main_loop = asyncio.get_event_loop()
asyncio.get_child_watcher().attach_loop(main_loop)
app = web.Application()

# Clear Chrome temporary profiles
dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)


class TimedLoop(object):
    cancelled = False

    def __init__(self, coro, duration):
        self.coro = coro
        self.duration = duration

    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.shutdown()

    def start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        task = asyncio.ensure_future(self._seek_result())
        task.add_done_callback(self._on_done)
        trigger = partial(self.loop.create_task, self._cancel_task(task))
        self.loop.call_later(self.duration, trigger)
        self.loop.run_forever()
        if not task.cancelled():
            result = task.result()
            return result

    def shutdown(self, *args, **kwargs):
        # Cancel all pending tasks in the loop
        pending = [
            self.loop.call_soon_threadsafe(partial(self._cancel_task, task))
            for task in asyncio.Task.all_tasks()
        ]
        asyncio.wait(pending,loop=self.loop)

    async def _seek_result(self):
        try:
            while 1:
                task = asyncio.ensure_future(
                    self.coro(),
                    loop=self.loop
                )
                await task
                if not task.cancelled():
                    result = task.result()
                    if result:
                        return result
        except CancelledError:
            await self._cancel_task(task)
            raise CancelledError
    
    def _on_done(self, task):
        self.loop.call_soon_threadsafe(self.loop.stop)
        
    async def _cancel_task(self, task):
        if not task.done():
            task.set_result(None)
            await task
    

async def work(pageurl, sitekey):
    proxy = asyncio.run_coroutine_threadsafe(
        proxies.get(), main_loop
    ).result()
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
    client = Solver(
        pageurl,
        sitekey,
        options=options,
        proxy=proxy
    )
    result = await client.start()
    if result:
        if result['status'] == "detected":
            asyncio.run_coroutine_threadsafe(
                proxies.set_banned(proxy), main_loop
            )
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
                with TimedLoop(coro, duration=10) as t:
                    result = await main_loop.run_in_executor(pool, t.start)
                print(result)
                if result:
                    response = {"solution": result}
                else:
                    response = {"error": "worker timed-out"}
    return web.json_response(response)


async def load_proxies():
    print('Loading proxies')
    while 1:
        protos = ["http://", "https://"]
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


#  Not sure if I need these here, will check later. And loop.add_signal_handler
#  might be the better option
def signal_handler(signal, frame):
    main_loop.stop()
    main_loop.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

app.router.add_get("/", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
