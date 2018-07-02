import asyncio
import sys

from nonocaptcha import util
from nonocaptcha.solver import Solver
from config import settings


if len(sys.argv) > 3:
    pageurl, sitekey, proxy = sys.argv[1:]
else:
    sys.exit(0)


async def work(pageurl, sitekey, proxy):
    try:
        # Chromium options and arguments
        options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
        client = Solver(pageurl, sitekey, options=options, proxy=proxy)
        result = await client.start()
        if result:
            return result
    except CancelledError:
        # Let's make sure Chrome closes after ungraceful exit
        if client.launcher:
            if not client.launcher.chromeClosed:
                await client.launcher.waitForChromeToClose()
        raise
     
result = asyncio.get_event_loop().run_until_complete(
    work(pageurl, sitekey, proxy)
)
if result:
    print(result)