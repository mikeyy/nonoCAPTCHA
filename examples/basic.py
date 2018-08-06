import asyncio
import signal
import sys

from nonocaptcha.solver import Solver

if len(sys.argv) == 3:
    pageurl, sitekey, proxy = sys.argv[1:]
else:
    print('Invalid number of arguments (pageurl, sitekey, proxy)')
    sys.exit(0)


options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
client = Solver(pageurl, sitekey, options=options, proxy=proxy)
try:
    result = loop.run_until_complete(client.start())
except CancelledError:
    raise
else:
    if result:
        print(result)
