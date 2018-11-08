import asyncio
import sys

from nonocaptcha.solver import Solver

if len(sys.argv) == 4:
    pageurl, sitekey, proxy = sys.argv[1:]
else:
    print('Invalid number of arguments (pageurl, sitekey, proxy)')
    sys.exit(0)


loop = asyncio.get_event_loop()
options = {
    "headless": False,
    "ignoreHTTPSErrors": True,
    "args": ["--timeout 5"]}
if proxy.lower() == "none":
    proxy = None
client = Solver(pageurl, sitekey, options=options, proxy=proxy)
try:
    result = loop.run_until_complete(client.start())
except asyncio.CancelledError:
    raise
else:
    if result:
        print(result)
