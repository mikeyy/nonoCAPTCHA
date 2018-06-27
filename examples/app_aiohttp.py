import asyncio
import random

from aiohttp import web, ClientSession, ClientError
from async_timeout import timeout
from collections import deque
from contextlib import suppress
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings


def shuffle(i):
    random.shuffle(i)
    return i


async def work(pageurl, sitekey, proxy):
    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
    async with timeout(10) as t:
        while 1:
            client = Solver(pageurl, sitekey, options=options, proxy=proxy)
            task = asyncio.ensure_future(client.start())
            await task
            result = task.result()
            if result:
                return result
    
            if t.expired:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
                return None




class Server(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.loop = asyncio.get_event_loop()
        self.proxy_source = settings["proxy_source"]
        self.proxies = None

    async def get_solution(self, request):
        while not self.proxies:
            await asyncio.sleep(1)

        params = request.rel_url.query
        pageurl = params['pageurl']
        sitekey = params['sitekey']
        if pageurl and sitekey:
            proxy = next(self.proxies)
            result = await work(pageurl, sitekey, proxy)
            if result:
                response = {'solution': result}
            else:
                response = {'error': 'worker timed-out'}
        else:
            response = {'error': 'invalid request'}
        return web.json_response(response)

    async def load_proxies(self):
        while 1:
            protos = ["http://", "https://"]
            if any(p in self.proxy_source for p in protos):
                f = util.get_page
            else:
                f = util.load_file
            
            try:
                result = await f(self.proxy_source)
            except:
                continue
            else:
                self.proxies = iter(shuffle(result.strip().split("\n")))
                await asyncio.sleep(10*60)

    async def start_background_tasks(self, app):
        app['dispatch'] = app.loop.create_task(self.load_proxies())

    async def cleanup_background_tasks(self, app):
        app['dispatch'].cancel()
        await app['dispatch']

    async def create_app(self):
        app = web.Application()
        app.router.add_get('/', self.get_solution)
        return app

    def run_app(self):
        loop = self.loop
        app = loop.run_until_complete(self.create_app())
        app.on_startup.append(self.start_background_tasks)
        app.on_cleanup.append(self.cleanup_background_tasks)
        web.run_app(app, host=self.host, port=self.port)


if __name__ == '__main__':
    s = Server(host='127.0.0.1', port=5000)
    s.run_app()