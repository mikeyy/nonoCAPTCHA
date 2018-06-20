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
        src = settings["proxy_source"]
        protos = ["http://", "https://"]
        if any(p in src for p in protos):
            f = util.get_page
        else:
            f = util.load_file
    
        result = await f(src)
        proxies = iter(shuffle(result.strip().split("\n")))
        await asyncio.sleep(10*60)


def loop_proxies(loop):
    asyncio.set_event_loop(loop)
    asyncio.ensure_future(get_proxies())


@backoff.on_predicate(backoff.constant, interval=1, max_time=60)
async def work(pageurl, sitekey):
    while not proxies:
        await asyncio.sleep(1)

    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}

    async with sem:
        proxy = next(proxies)

        client = Solver(pageurl, sitekey, options=options, proxy=proxy)

        answer = await client.start()

        if answer:
            print(answer)
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
    loop = asyncio.get_event_loop()
    t = threading.Thread(target=loop_proxies, args=(loop,))
    t.start()

    app.run("0.0.0.0", 5000, loop=loop)
