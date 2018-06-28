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
            proxies = iter(shuffle(result.strip().split("\n")))
            await asyncio.sleep(10*60)


async def work(pageurl, sitekey):
    
    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
    
    result = None
    while 1:
        try:
            proxy = next(proxies) if proxy_src else None
            client = Solver(pageurl, sitekey, options=options, proxy=proxy)
            result = await client.start()
        finally:
            await client.kill_chrome()
            if result:
                return result

@app.route("/get", methods=["GET", "POST"])
async def get():
    while not proxies:
        await asyncio.sleep(1)

    if not request.args:
        result = "Invalid request"
    else:
        pageurl = request.args.get("pageurl")
        sitekey = request.args.get("sitekey")
        if not pageurl or not sitekey:
            result = "Missing sitekey or pageurl"
        else:
            try:
                result = await asyncio.wait_for(work(pageurl, sitekey), 3*60)
            except asyncio.TimeoutError:
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
    app.run("0.0.0.0", 8000, loop=loop)
