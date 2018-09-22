#!/home/carlo/nonoCAPTCHA/venv/bin/python3.6

from nonocaptcha.solver import Solver

import asyncio

pageurl = "https://www.google.com/recaptcha/api2/demo"
sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

client = Solver(
    pageurl,
    sitekey,
    proxy='127.0.0.1:8123'
)

loop = asyncio.get_event_loop()
loop.run_until_complete(client.start())
loop.run_until_complete(client.cleanup())
