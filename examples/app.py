import asyncio
import random
import shutil
import signal
import sys
import subprocess

from aiohttp import web, ClientSession, ClientError
from async_timeout import timeout
from asyncio import TimeoutError, CancelledError
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from nonocaptcha import util, settings
from nonocaptcha.solver import Solver

proxy_source = settings["proxy"]["source"]

dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)

app = web.Application()

def shuffle(i):
    random.shuffle(i)
    return i


async def work(pageurl, sitekey):
    async with timeout(60) as timer:
        while not timer.expired:
            try:
                proxy = next(proxies)
                # Chromium options and arguments
                options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
                client = Solver(pageurl, sitekey, options=options, proxy=proxy)
                result = await client.start()
                if result:
                    return result
            except CancelledError:
                break

    if client.launcher:
        if not client.launcher.chromeClosed:
            await client.launcher.waitForChromeToClose()


async def get_solution(request):
    while not proxies:
        await asyncio.sleep(1)
    params = request.rel_url.query
    pageurl = params["pageurl"]
    sitekey = params["sitekey"]
    response = {"error": "invalid request"}
    if pageurl and sitekey:
        result = await work(pageurl, sitekey)
        if result:
            response = {"solution": result}
        else:
            response = {"error": "worker timed-out"}
    return web.json_response(response)


proxies = None
async def load_proxies():
    global proxies
    print('Loading proxies')
    while 1:
        protos = ["http://", "https://"]
        if any(p in proxy_source for p in protos):
            f = util.get_page
        else:
            f = util.load_file

        try:
            result = await f(proxy_source)
        except:
            continue
        else:
            proxies = iter(shuffle(result.strip().split("\n")))
            print('Proxies loaded')
            await asyncio.sleep(10 * 60)


async def start_background_tasks(app):
    app["dispatch"] = app.loop.create_task(load_proxies())


async def cleanup_background_tasks(app):
    app["dispatch"].cancel()
    await app["dispatch"]


def signal_handler(signal, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

app.router.add_get("/get", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=5000)
