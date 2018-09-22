import asyncio
from nonocaptcha.solver import Solver

pageurl = "https://www.google.com/recaptcha/api2/demo"
sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

proxy = "127.0.0.1:1000"
auth_details = {"username": "user", "password": "pass"}
args = ["--timeout 5"]
options = {"ignoreHTTPSErrors": True, "args": args}
client = Solver(
    pageurl, sitekey, options=options, proxy=proxy, proxy_auth=auth_details
)

solution = asyncio.get_event_loop().run_until_complete(client.start())
if solution:
    print(solution)
