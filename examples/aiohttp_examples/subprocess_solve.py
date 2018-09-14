import asyncio
import signal
import sys

from nonocaptcha.solver import Solver

if len(sys.argv) > 3:
    pageurl, sitekey, proxy, proxy_username, proxy_password = sys.argv[1:]
else:
    sys.exit(0)


async def kill_chrome():
    if client.launcher:
        if not client.launcher.chromeClosed:
            await client.launcher.waitForChromeToClose()


def signal_handler(signal, frame):
    asyncio.ensure_future(kill_chrome())


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

try:
    proxy_auth = {"username": proxy_username,
                  "password": proxy_password}
    options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
    client = Solver(
        pageurl,
        sitekey,
        options=options,
        proxy=proxy,
        proxy_auth=proxy_auth
    )
    result = asyncio.get_event_loop().run_until_complete(
        client.start()
    )
except asyncio.CancelledError:
    asyncio.get_event_loop().run_until_complete(
        kill_chrome()
    )
else:
    if result:
        print(result)
