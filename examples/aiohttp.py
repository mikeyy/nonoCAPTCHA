import asyncio
import random
import signal
import shutil
import sys

from aiohttp import web
from async_timeout import timeout
from asyncio import CancelledError
from pathlib import Path

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRETKEY= "CHANGEME"

proxy_source = None  # Can be URL or file location
proxies = ProxyDB(last_banned_timeout=45*60)

dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)

app = web.Application()
loop = asyncio.get_event_loop()


def shuffle(i):
    random.shuffle(i)
    return i


async def work(pageurl, sitekey, proxy):
    while 1:
        proxy = await proxies.get()
        if proxy:
            if "@" in proxy:
                proxy_details = proxy.split("@")
                proxy = proxy_details[1]
                username, password = proxy_details[0].split(":")
                proxy_auth = {"username": username, "password": password}
            options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
            client = Solver(
                pageurl,
                sitekey,
                options=options,
                proxy=proxy,
                proxy_auth=proxy_auth
            )
            try:
                result = await client.start()
                if isinstance(result, dict):
                    if 'code' in result:
                        return result
            except CancelledError:
                return


async def get_solution(request):
    params  = await request.post()
    pageurl = params.get("pageurl")
    sitekey = params.get("sitekey")
    secret_key = params.get("secret_key")
    response = {"error": ""}
    if not pageurl or not sitekey or not secret_key:
        response["error"] = "invalid request"
    else:
        if secret_key != SECRETKEY:
            response["error"] = "unauthorized attempt"
        else:
            if pageurl and sitekey:
                result = await work(pageurl, sitekey)
                if result:
                    if 'code' in result:
                        response["solution"] = result['code']
                    else:
                        response["error"] = result['status']
                        # Should we update last_blocked for this?
                        # if result['status'] == 'detected':
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
