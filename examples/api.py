import asyncio
import signal
import shutil
import sys

from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRET_KEY = "CHANGEME"

proxy_source = None  # Can be URL or file location
proxies = ProxyDB(last_banned_timeout=45*60)

parent_loop = asyncio.get_event_loop()
asyncio.set_child_watcher(asyncio.FastChildWatcher())
asyncio.get_child_watcher().attach_loop(parent_loop)

app = web.Application()

# Clear Chrome temporary profiles
dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)


class TimedLoop(object):
    def __init__(self, coro, duration, loop=None):
        self._coro = coro
        self._duration = duration
        self._loop = loop or asyncio.get_event_loop()
        #  Haven't tried ProcessPoolExecutor. Perfomance gains are doubtful,
        #  presumingly detrimental.
        self._executor = ThreadPoolExecutor()
        self._main_task = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, exc_type, tb):
        asyncio.run_coroutine_threadsafe(self.cleanup(), self._thread_loop)
        return self

    def __await__(self):
        return self.start().__await__()

    async def start(self):
        #  Due to uncertaintity of thread, evoke a new event loop prior to
        #  thread initiation.
        self._thread_loop = asyncio.new_event_loop()
        #  TODO Benchmark each thread spawning mechanisms
        #  For example, threading.Thread() and self.executor.submit()
        self._loop.run_in_executor(
            self._executor, self.thread_loop, self._thread_loop)
        future = asyncio.Future()
        self._thread_loop.call_soon_threadsafe(
                self._thread_loop.create_task, self.timed_continuity(future))
        try:
            await future
            result = future.result()
        except(asyncio.CancelledError, asyncio.TimeoutError):
            result = None
        finally:
            return result

    def thread_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def timed_continuity(self, future):
        this = asyncio.Task.current_task(loop=self._thread_loop)
        self._thread_loop.call_later(self._duration, this.cancel)
        try:
            while True:
                result = await self._coro()
                if result is not None:
                    break
        except(asyncio.CancelledError, asyncio.TimeoutError):
            result = None
        finally:
            self._loop.call_soon_threadsafe(future.set_result, result)

    async def cleanup(self):
        pending = tuple(
            task for task in asyncio.Task.all_tasks(loop=self._thread_loop)
            if task is not asyncio.Task.current_task())
        asyncio.gather(
            *pending, return_exceptions=True,
            loop=self._thread_loop).cancel()
        self._thread_loop.call_soon_threadsafe(self._thread_loop.stop)
        self._executor.shutdown()


async def work(pageurl, sitekey):
    proxy = asyncio.run_coroutine_threadsafe(
        proxies.get(), parent_loop).result()
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
                proxies.set_banned(proxy), parent_loop)
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
                async with TimedLoop(coro, duration=180) as t:
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
    parent_loop.stop()
    parent_loop.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

app.router.add_get("/", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
