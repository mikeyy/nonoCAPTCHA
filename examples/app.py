import asyncio
import backoff
import random
import sys
import time

from async_timeout import timeout
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from multiprocessing import cpu_count
from threading import Thread
from quart import Quart, Response, request

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings

# Max threads to use in Pool
threads = 100
app = Quart(__name__)


def shuffle(i):
    random.shuffle(i)
    return i


def new_event_loop(pool_size=None):
    pool_size = pool_size or cpu_count()
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.new_event_loop()
    thread_pool = ThreadPoolExecutor(pool_size)
    loop.set_default_executor(thread_pool)
    asyncio.set_event_loop(loop)
    return loop


proxies = None
async def get_proxies():
    global proxies

    asyncio.set_event_loop(new_event_loop())
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

    if proxy_src:
        proxy = next(proxies)
    else:
        proxy = None
    
    client = Solver(pageurl, sitekey, options=options, proxy=proxy)
    answer = await client.start()
    if answer:
        return answer


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
            async with timeout(180) as t:
                while 1:
                    task = asyncio.ensure_future(work(pageurl, sitekey), loop=loop)
                    await task
                    result = task.result()
                    if result or t.expired:
                        break
            if not result:
                result = "Request timed-out, please try again"           
    return Response(result, mimetype="text/plain")


loop = new_event_loop()
proxy_src = settings["proxy_source"]
if proxy_src:
    asyncio.ensure_future(get_proxies())
    
if __name__ == "__main__":
    app.run("0.0.0.0", 5000, loop=loop)
