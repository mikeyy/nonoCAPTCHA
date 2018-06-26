import asyncio
import os
import random
import shutil
import sys
import time

from async_timeout import timeout
from contextlib import suppress
from pathlib import Path
from quart import Quart, Response, request

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings

count = 100

sem = asyncio.Semaphore(count)
app = Quart(__name__)


def shuffle(i):
    random.shuffle(i)
    return i


proxies = None
async def get_proxies():
    global proxies

    asyncio.set_event_loop(asyncio.get_event_loop())
    while 1:
        protos = ["http://", "https://"]
        if any(p in proxy_src for p in protos):
            f = util.get_page
        else:
            f = util.load_file
        
        try:
            result = await f(proxy_src)
        except:
            continue
        else:
            proxies = shuffle(result.strip().split("\n"))
            await asyncio.sleep(10*60)


async def work(pageurl, sitekey):
    
    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}

    if proxy_src:
        proxy = random.choice(proxies)
    else:
        proxy = None

    async with sem:
        client = Solver(pageurl, sitekey, options=options, proxy=proxy)
        try:
            task = asyncio.ensure_future(client.start())
            await task
        except:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        else:
            return task.result()


@app.route("/get", methods=["GET", "POST"])
async def get():
    while not proxies:
        await asyncio.sleep(1)

    result = None
    if not request.args:
        result = "Invalid request"
    else:
        pageurl = request.args.get("pageurl")
        sitekey = request.args.get("sitekey")
        if not pageurl or not sitekey:
            result = "Missing sitekey or pageurl"
        else:
            async with timeout(1) as t:
                while 1:
                    task = asyncio.ensure_future(work(pageurl, sitekey))
                    await task
                    result = task.result()
                    if result:
                        break

                    if t.expired:
                        task.cancel()
                        with suppress(asyncio.CancelledError):
                            await task
                        break

            if not result:
                result = "Request timed-out, please try again"        
    return Response(result, mimetype="text/plain")


home = Path.home()
dir = f'{home}/.pyppeteer/.dev_profile'
shutil.rmtree(dir, ignore_errors=True)

loop = asyncio.get_event_loop()
proxy_src = settings["proxy_source"]
if proxy_src:
    asyncio.ensure_future(get_proxies())

if __name__ == "__main__":
    app.run("0.0.0.0", 5000, loop=loop)
