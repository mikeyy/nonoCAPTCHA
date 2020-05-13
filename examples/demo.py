from goodbyecaptcha.solver import Solver

pageurl = "https://www.google.com/recaptcha/api2/demo"
sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

proxy = "127.0.0.1:1000"
auth_details = {"username": "user", "password": "pass"}
args = ["--timeout 5"]
options = {"ignoreHTTPSErrors": True, "args": args}  # References: https://miyakogi.github.io/pyppeteer/reference.html
client = Solver(
    # With Proxy
    # pageurl, sitekey, options=options, proxy=proxy, proxy_auth=auth_details
    # Without Proxy
    pageurl, sitekey, options=options
)

solution = client.loop.run_until_complete(client.start())
if solution:
    print(solution)
