import time
import random
import asyncio
import backoff
import threading

from async_timeout import timeout
from quart import Quart, Response, request

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings

# Max browsers to open/threads
count = 10

app = Quart(__name__)
sem = asyncio.Semaphore(count)


def shuffle(i):
    random.shuffle(i)
    return i


proxies = None
async def get_proxies():
    global proxies
    while 1:
        protos = ["http://", "https://"]
        if any(p in proxy_src for p in protos):
            f = util.get_page
        else:
            f = util.load_file
    
        result = await f(proxy_src)
        proxies = iter(shuffle(result.strip().split("\n")))
        await asyncio.sleep(10*60)


def loop_proxies():
    asyncio.ensure_future(get_proxies(), loop=loop)


@backoff.on_predicate(backoff.constant, interval=1, max_time=60)
async def work(pageurl, sitekey):
    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}

    async with sem:
        if proxy_source:
            proxy = next(proxies)
        else:
            proxy = None

        client = Solver(pageurl, sitekey, options=options, proxy=proxy)

        answer = await client.start()

        if answer:
            return answer


@app.route("/get", methods=["GET", "POST"])
async def get():
    if not request.args:
        result = "Invalid request"
    else:
        pageurl = request.args.get("pageurl")
        sitekey = request.args.get("sitekey")
        if not pageurl or not sitekey:
            result = "Missing sitekey or pageurl"
        else:
            result = await work(pageurl, sitekey)
            if not result:
                result = "Request timed-out, please try again"
    return Response(result, mimetype="text/plain")


if __name__ == "__main__":
    proxy_src = settings["proxy_source"]
    if proxy_src:
        loop = asyncio.get_event_loop()
        t = threading.Thread(target=loop_proxies, args=(loop,))
        t.start()
        
        while not proxies:
            asyncio.sleep(1)

    app.run("0.0.0.0", 5000, loop=loop)
