import asyncio
import sys

from nonocaptcha.solver import Solver

if len(sys.argv) > 3:
    pageurl, sitekey, proxy = sys.argv[1:]
else:
    sys.exit(0)


async def work(pageurl, sitekey, proxy):
    try:
        options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
        client = Solver(pageurl, sitekey, options=options, proxy=proxy)
        result = await client.start()
        if result:
            return result
    except asyncio.CancelledError:
        if client.launcher:
            if not client.launcher.chromeClosed:
                await client.launcher.waitForChromeToClose()
        raise

result = asyncio.get_event_loop().run_until_complete(
    work(pageurl, sitekey, proxy)
)
if result:
    print(result)
