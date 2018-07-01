import asyncio
import json
import random
import shutil
import sys
import time

from pathlib import Path
from quart import Quart, Response, request

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings

count = 100

sem = asyncio.Semaphore(count)
app = Quart(__name__)
tasks = {}


# Celery doesn't work with asyncio at the moment, here is some pseudotasking!
# Don't use this, really. Once Celery v5 is released, an example will be here.


def shuffle(i):
    random.shuffle(i)
    return i


proxies = None


async def get_proxies():
    global proxies

    asyncio.set_event_loop(asyncio.get_event_loop())
    while True:
        protos = ["http://", "https://"]
        if any(p in proxy_src for p in protos):
            f = util.get_page
        else:
            f = util.load_file

        try:
            result = await f(proxy_src)
        except BaseException:
            continue
        else:
            proxies = shuffle(result.strip().split("\n"))
            await asyncio.sleep(10 * 60)


async def work(pageurl, sitekey, task_id):

    # Chromium options and arguments
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}

    async with sem:
        while True:
            if proxy_src:
                proxy = random.choice(proxies)
            else:
                proxy = None

            client = Solver(pageurl, sitekey, options=options, proxy=proxy)
            task = asyncio.ensure_future(client.start())
            await task
            result = task.result()
            if result:
                break

        tasks.update({task_id: {"status": "finished", "solution": result}})


@app.route("/get_task_result", methods=["GET", "POST"])
async def get_task_result():
    task_id = request.args.get("task_id")
    if not task_id:
        result = "Missing required argument `taskid`"
    else:
        if task_id not in tasks:
            response = {"error": "invalid task_id"}
        else:
            status = tasks[task_id]["status"]
            response = {"task_id": task_id, "status": status}
            if "solution" in tasks[task_id]:
                solution = tasks[task_id]["solution"]
                response.update({"solution": solution})
        result = json.dumps(response)
    return Response(result, mimetype="text/json")


@app.route("/create_task", methods=["GET", "POST"])
async def create_task():
    while not proxies:
        await asyncio.sleep(1)

    pageurl = request.args.get("pageurl")
    sitekey = request.args.get("sitekey")
    if not pageurl or not sitekey:
        result = "Missing `sitekey` or `pageurl`"
    else:
        task_id = "".join(
            random.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for x in range(8)
        )
        tasks.update({task_id: {"status": "processing"}})
        asyncio.ensure_future(work(pageurl, sitekey, task_id))
        result = json.dumps({"task_id": task_id})
    return Response(result, mimetype="text/json")


home = Path.home()
dir = f"{home}/.pyppeteer/.dev_profile"
shutil.rmtree(dir, ignore_errors=True)

loop = asyncio.get_event_loop()
proxy_src = settings["proxy_source"]
if proxy_src:
    asyncio.ensure_future(get_proxies())

if __name__ == "__main__":
    app.run("0.0.0.0", 5000, loop=loop)
