import asyncio
import shutil

from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from threading import RLock, Event

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


#  Bugs are to be expected, despite my efforts. Apparently, event loops paired
#  with threads is nothing short of a hassle. A transition to an alternative
#  asynchronized library is a probable recourse. Unless, I'm doing something
#  wrong, help is appreciated.
class TaskRerun(object):

    def __init__(self, coro, duration):
        self.coro = coro
        self.duration = duration
        self._executor = ThreadPoolExecutor()
        self._lock = RLock()
        self._cancel = Event()

    def __del__(self):
        #  However we are able to exit with Ctrl+C using executor greacefully,
        #  contrary to the aiohttp_thread.py example.
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop.close()

    async def __aenter__(self):
        self._executor.submit(self.prepare_loop)
        return self

    async def __aexit__(self, exc, exc_type, tb):
        asyncio.run_coroutine_threadsafe(
            self.cleanup(self._loop), self._loop)
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
            #  Set appropiate results for the Future.
            try:
                future.set_result(task.result())
            except asyncio.CancelledError:
                future.set_result(None)
            except Exception as e:
                future.set_result(task.exception())
            #  Set the event to inform the Task to break from loop. Not sure if
            #  we need to wrap this in an call_soon_threadsafe.
            self._cancel.set()
        future = asyncio.get_event_loop().create_future()
        #  Deadlock occurs unless we wrap the future.
        task = asyncio.wrap_future(
            asyncio.run_coroutine_threadsafe(self.seek(loop), loop), loop=loop)
        task.add_done_callback(partial(callback, future))
        #  Imitate a Timeout by using call_later to invoke task cancellation.
        loop.call_soon_threadsafe(loop.call_later, self.duration, task.cancel)
        try:
            #  Wait for Future to set the result
            await future
            result = future.result()
        except BaseException as e:
            # Consume Exception to make event loop happy
            raise e
        finally:
            return result

    async def seek(self, loop):
        #  Maybe this loop can replaced with recursion, considering it's
        #  unlikely we'll exceed 1000
        while True:
            try:
                result = await self.coro(loop)
                if result is not None:
                    return result
            except BaseException as e:
                # Consume Exception to send to Future
                raise e
            finally:
                #  Break if event was set
                if self._cancel.is_set():
                    break

    async def cleanup(self, loop):
        pending = tuple(
            task for task in asyncio.Task.all_tasks(loop=loop)
            if task is not asyncio.Task.current_task())
        gathered = asyncio.gather(*pending, loop=loop)
        gathered.cancel()
        #  Wait for pending tasks to finish cancelling.
        await gathered


async def work(pageurl, sitekey, loop):
    proxy = proxies.get()
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
