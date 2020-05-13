from goodbyecaptcha.solver import Solver

pageurl = "https://www.google.com/recaptcha/api2/demo"
sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

proxy = "127.0.0.1:1000"
auth_details = {"username": "user", "password": "pass"}
args = ["--timeout 5"]
options = {"ignoreHTTPSErrors": True, "args": args}


class MySolver(Solver):
    async def on_goto(self):
        # Set Cookies and other stuff
        await self.page.setCookie({
            'name': 'cookie1',
            'value': 'value1',
            'domain': '.google.com'
        })
        self.log('Cookies ready!')

    async def on_start(self):
        # Set or Change data
        self.log('Set data in form ...')
        await self.page.type('input[name="input1"]', 'value')

    async def on_finish(self):
        # Click button Send
        self.log('Clicking send button ...')
        await self.page.click('input[id="recaptcha-demo-submit"]')
        await self.page.waitForNavigation()
        await self.page.screenshot({'path': 'image.png'})


client = MySolver(
    # With Proxy
    pageurl, sitekey, options=options, proxy=proxy, proxy_auth=auth_details
    # Without Proxy
    # pageurl, sitekey, options=options
)

client.loop.run_until_complete(client.start())
