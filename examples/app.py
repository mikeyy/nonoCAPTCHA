import asyncio
import random

from aiohttp import web, ClientSession, ClientError
from async_timeout import timeout
from collections import deque
from functools import partial

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings

proxy_source = settings["proxy_source"]
proxies = None

app = web.Application()


def shuffle(i):
    random.shuffle(i)
    return i


async def work(pageurl, sitekey, proxy):
    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
    with timeout(3*60) as timer:
        try:
            while not timer.expired:
                client = Solver(pageurl, sitekey, options=options, proxy=proxy)
                result = await client.start()
                if result:
                    return result
        except asyncio.CancelledError:
            await client.kill_chrome()


async def get_solution(request):
    while not proxies:
        await asyncio.sleep(1)

    params = request.rel_url.query
    pageurl = params['pageurl']
    sitekey = params['sitekey']
    response = {'error': 'invalid request'}
    if pageurl and sitekey:
        proxy = next(proxies)
        result = await work(pageurl, sitekey, proxy)
        if result:
            response = {'solution': result}
        else:
            response = {'error': 'worker timed-out'}
    return web.json_response(response)


async def load_proxies():
    global proxies
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
            await asyncio.sleep(10*60)


async def start_background_tasks(app):
    app['dispatch'] = app.loop.create_task(load_proxies())


async def cleanup_background_tasks(app):
    app['dispatch'].cancel()
    await app['dispatch']

app.router.add_get('/get', get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=5000)
