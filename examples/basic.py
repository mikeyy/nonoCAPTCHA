import asyncio
import sys

from goodbyecaptcha.solver import Solver

if len(sys.argv) == 3:
    pageurl, proxy = sys.argv[1:]
else:
    print('Invalid number of arguments (pageurl, proxy)')
    sys.exit(0)

options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
if proxy.lower() == "none":
    proxy = None
client = Solver(pageurl, options=options, proxy=proxy)
try:
    result = client.loop.run_until_complete(client.start())
except asyncio.CancelledError:
    raise
else:
    if result:
        print(result)
