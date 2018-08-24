import asyncio
import signal
import shutil
import sys

from aiohttp import web
from asyncio import CancelledError
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRET_KEY = "CHANGEME"

proxy_source = None  # Can be URL or file location
proxies = ProxyDB(last_banned_timeout=45*60)

loop = asyncio.get_event_loop()
asyncio.set_child_watcher(asyncio.FastChildWatcher())
asyncio.get_child_watcher().attach_loop(loop)

app = web.Application()

# Clear Chrome temporary profiles
dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)


class TimedLoop(object):
    def __init__(self, coro, duration, executor=None):
        self._coro = coro
        self._duration = duration
        self._parent_task = None
        self._executor = executor if executor else ThreadPoolExecutor()

    async def __aenter__(self):
        self._parent_task = asyncio.Task.current_task()
        return self

    async def __aexit__(self, *args):
        asyncio.get_event_loop().call_soon(self._parent_task.cancel)

    def __await__(self):
        return (yield from self.start)

    async def start(self):
        result = await asyncio.get_event_loop().run_in_executor(
            self._executor, self.setup_loop
        )
        return result

    def setup_loop(self):
        thread_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread_loop)
        task = thread_loop.create_task(self.continuous(thread_loop))
        thread_loop.call_later(self._duration, task.cancel)
        try:
            try:
                thread_loop.run_until_complete(task)
            finally:
                thread_loop.create_task(self.cancel(thread_loop))
                thread_loop.run_forever()
        finally:
            thread_loop.call_soon(thread_loop.close)
            return task.result() if not task.cancelled() else None

    async def cancel(self, loop):
        def silence_gathered(future):
            try:
                future.result()
            except Exception:
                pass

        tasks = [
            task for task in asyncio.Task.all_tasks(loop=loop)
            if asyncio.Task.current_task() is not task
        ]
        gathered = asyncio.gather(*tasks, loop=loop)
        gathered.add_done_callback(silence_gathered)
        gathered.cancel()
        try:
            await gathered
        finally:
            loop.call_soon(loop.stop)

    async def continuous(self, loop):
        try:
            while True:
                task = loop.create_task(self._coro())
                await task
                result = task.result()
                if result:
                    return result
        except CancelledError:
            task.cancel()
            await task
            raise


async def work(pageurl, sitekey):
    proxy = asyncio.run_coroutine_threadsafe(
        proxies.get(), loop
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
                proxies.set_banned(proxy), loop
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
                async with TimedLoop(coro, duration=60) as t:
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
    loop.stop()
    loop.close()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

app.router.add_get("/", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
