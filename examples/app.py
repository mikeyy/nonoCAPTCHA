import asyncio
import random
import signal
import shutil
import sys

from aiohttp import web
from async_timeout import timeout
from asyncio import CancelledError
from pathlib import Path

from nonocaptcha import util, settings
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

proxy_source = settings["proxy"]["source"]
proxies = ProxyDB(last_used_timeout=10*60, last_banned_timeout=30*60)

dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)

app = web.Application()
loop = asyncio.get_event_loop()


def shuffle(i):
    random.shuffle(i)
    return i


async def work(pageurl, sitekey):
    async with timeout(3*60) as timer:
        while not timer.expired:
            proxy = await proxies.get()
            if proxy:
                # Chromium options and arguments
                options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
                client = Solver(pageurl, sitekey, options=options, proxy=proxy)
                try:
                    result = await client.start()
                    if result:
                        if result['status'] == "detected":
                            proxies.set_banned(proxy)
                        else:
                            proxies.set_used(proxy)
                            if result['status'] == "success":
                                return result['code']
                except CancelledError:
                    return


async def get_solution(request):
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


def signal_handler(signal, frame):
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

app.router.add_get("/get", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)
