import asyncio
import signal
import sys

from nonocaptcha.solver import Solver

if len(sys.argv) == 3:
    pageurl, sitekey, proxy = sys.argv[1:]
else:
    print('Invalid number of arguments (pageurl, sitekey, proxy)')
    sys.exit(0)


async def handle_signal(signame):
    if not task.cancelled():
        task.cancel()


loop = asyncio.get_event_loop()
for signame in ('SIGINT', 'SIGTERM'):
    loop.add_signal_handler(
                                getattr(signal, signame),
                                lambda: asyncio.ensure_future(
                                    handle_signal(signame)
                                )
                            )


options = {"ignoreHTTPSErrors": True, "args": ["--timeout 5"]}
client = Solver(pageurl, sitekey, options=options, proxy=proxy)
task = asyncio.ensure_future(client.start())
result = loop.run_until_complete(task)
loop.run_until_complete(client.cleanup())
if not task.cancelled():
    if result:
        print(result)