#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import asyncio
import shutil

from aiohttp import web
from async_timeout import timeout
from functools import partial
from pathlib import Path

from nonocaptcha import util
from nonocaptcha.proxy import ProxyDB
from nonocaptcha.solver import Solver

SECRET_KEY = "CHANGEME"

proxies = ProxyDB(last_banned_timeout=45*60)
proxy_source = None  # Can be URL or file location
proxy_username, proxy_password = (None, None)

parent_loop = asyncio.get_event_loop()

app = web.Application()

# Clear Chrome temporary profiles
dir = f"{Path.home()}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)


async def work(pageurl, sitekey):  
    async with timeout(180):
        while 1:
            proxy = proxies.get()
            if proxy:
                try:
                    proc = await asyncio.subprocess.create_subprocess_exec(
                        *["python",
                        "solve.py",
                        pageurl,
                        sitekey,
                        proxy,
                        proxy_username,
                        proxy_password],
                        stdout=asyncio.subprocess.PIPE,
                    )
                    await proc.wait()
                    return_code = proc.returncode
                    if not return_code:
                        buffer = await proc.stdout.read()
                        result = buffer.decode("ascii").strip("\n")
                        if result:
                            result = eval(result)
                            if result['status'] == "detected":
                                parent_loop.call_soon_threadsafe(
                                    proxies.set_banned, proxy)
                            else:
                                if result['status'] == "success":
                                    return result['code']
                except asyncio.CancelledError:
                    proc.terminate()
                    await proc.wait()
                    return


async def get_solution(request):
    params = request.rel_url.query
    pageurl = params.get("pageurl")
    sitekey = params.get("sitekey")
    secret_key = params.get("secret_key")
    if not pageurl or not sitekey or not secret_key:
        response = {"error": "invalid request"}
    else:
        if secret_key != SECRET_KEY:
            response = {"error": "unauthorized attempt logged"}
        else:
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
        if proxy_source is None:
            return
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


app.router.add_get("/", get_solution)
app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=5000)
