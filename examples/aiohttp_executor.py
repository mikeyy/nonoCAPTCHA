import asyncio
import shutil

from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from threading import Lock

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRET_KEY = "CHANGEME"

proxy_source = None  # Can be URL or file location
proxies = ProxyDB(last_banned_timeout=45*60)

parent_loop = asyncio.get_event_loop()
#  I'm not sure exactly if FastChildWatcher() is really any faster, requires
#  future research.
asyncio.set_child_watcher(asyncio.FastChildWatcher())
asyncio.get_child_watcher().attach_loop(parent_loop)

app = web.Application()

# Clear Chrome temporary profiles
dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)


class TaskRerun(object):
    def __init__(self, coro, duration):
        self._coro = coro
        self._duration = duration
        #  ProcessPoolExecutor was not explored. Might be worth a try.
        self._executor = ThreadPoolExecutor()
        self._lock = Lock()

    async def __aenter__(self):
        self._executor.submit(self.prepare_loop)
        return self

    async def __aexit__(self, exc, exc_type, tb):
        asyncio.run_coroutine_threadsafe(self.cleanup(self._loop), self._loop)
        return self

    def prepare_loop(self):
        #  Surrounding the context around run_forever never releases the lock!
        with self._lock:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def start(self):
        with self._lock:
            return await self._start(self._loop)

    async def _start(self, loop):
        def callback(future, task):
            try:
                future.set_result(task.result())
            except asyncio.CancelledError:
                future.set_result(None)
            except Exception:
                future.set_result(task.exception())

        #  We use a Future for setting a result since the task runs in a
        #  separate thread. Otherwise, an "Task attached to a different loop"
        #  exception is raised
        future = asyncio.Future()
        #  Here wrap_future is used to assure task cancels gracefully; on the.
        #  contrary, run_coroutine_threadsafe terminates immediately which
        #  leaves browers running and temporariy created folders wasting space.
        task = asyncio.wrap_future(
                asyncio.run_coroutine_threadsafe(self.seek(loop), loop))
        task.add_done_callback(partial(callback, future))
        loop.call_soon_threadsafe(loop.call_later, self._duration, task.cancel)
        try:
            await future
            result = future.result()
        except Exception as exc:
            result = None
        finally:
            return result

    async def seek(self, loop):
        #  Maybe this loop can replaced with recursion, considering it's
        #  doubtful we'll exceed 1000
        while True:
            result = await self._coro(loop)
            if result is not None:
                return result

    async def cleanup(self, loop):
        pending = tuple(
            task for task in asyncio.Task.all_tasks(loop=loop)
            if task is not asyncio.Task.current_task())
        asyncio.gather(
            *pending, return_exceptions=True, loop=loop).cancel()
        #  However we are able to exit with Ctrl+C using executor greacefully,
        #  contrary to the aiohttp_thread.py example.
        loop.call_soon_threadsafe(loop.stop)


async def work(pageurl, sitekey, loop):
    proxy = await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
        proxies.get(), parent_loop))
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
    client = Solver(
        pageurl,
        sitekey,
        loop=loop,
        options=options,
        proxy=proxy
    )
    result = await client.start()
    if result:
        if result['status'] == "detected":
            await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                proxies.set_banned(proxy), parent_loop))
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
                async with TaskRerun(coro, duration=30) as t:
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
    pass


async def cleanup_background_tasks(app):
    app["dispatch"].cancel()
    await app["dispatch"]
    pass

app.router.add_get("/", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
