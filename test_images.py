import asyncio
import time

from nonocaptcha.solver import Solver

print('Test NonoCaptcha')
pageurl = "https://www.google.com/recaptcha/api2/demo"
sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"
timeout = 60
method = 'images'
args = ['--timeout 60']
options = {"ignoreHTTPSErrors": True, "method": method, "headless": False, "args": args}

client = Solver(pageurl, sitekey, options=options)
start = time.time()
while True:
    # Timeout
    if timeout:
        if timeout < (time.time() - start):
            print('TIME OUT')
            break
    solution = asyncio.get_event_loop().run_until_complete(client.start())
    if solution:
        if solution['status'] != 'success':
            continue
        # Solution Found
        elapsed = time.time() - start
        print("Time complete: {0}".format(elapsed))
        break
