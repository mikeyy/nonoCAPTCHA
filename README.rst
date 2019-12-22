.. image:: https://img.shields.io/pypi/v/goodbyecaptcha.svg
    :alt: PyPI
    :target: https://pypi.org/project/goodbyecaptcha/
.. image:: https://img.shields.io/pypi/pyversions/goodbyecaptcha.svg
    :alt: PyPI - Python Version
    :target: https://pypi.org/project/goodbyecaptcha/
.. image:: https://img.shields.io/pypi/l/goodbyecaptcha.svg
    :alt: PyPI - License
    :target: https://pypi.org/project/goodbyecaptcha/
.. image:: https://img.shields.io/pypi/status/goodbyecaptcha.svg
    :alt: PyPI - Status
    :target: https://pypi.org/project/goodbyecaptcha/

GoodByeCaptcha
==============

An async Python library to automate solving ReCAPTCHA v2 by images/audio using
Mozilla's DeepSpeech, PocketSphinx, Microsoft Azure’s, Google Speech and
Amazon's Transcribe Speech-to-Text API. Also image recognition to detect
the object suggested in the captcha. Built with Pyppeteer for Chrome
automation framework and similarities to Puppeteer, PyDub for easily
converting MP3 files into WAV, aiohttp for async minimalistic web-server,
and Python’s built-in AsyncIO
for convenience.

Disclaimer
----------

This project is for educational and research purposes only. Any actions
and/or activities related to the material contained on this GitHub
Repository is solely your responsibility. The misuse of the information
in this GitHub Repository can result in criminal charges brought against
the persons in question. The author will not be held responsible in the
event any criminal charges be brought against any individuals misusing
the information in this GitHub Repository to break the law.

Preview
-------

Check out 1-minute presentation of the script in action

.. image:: https://img.youtube.com/vi/zgwetyKmg5g/0.jpg
   :target: https://www.youtube.com/watch?v=zgwetyKmg5g

Compatibility
-------------

Linux, macOS, and Windows!

Requirements
------------

Python
`3.7.0 <https://www.python.org/downloads/release/python-370/>`__,
`FFmpeg <https://ffmpeg.org/download.html>`__, a `Microsoft
Azure <https://portal.azure.com/>`__ account for Bing Speech API access, an
Amazon Web Services account for Transcribe and S3 access, Wit.AI, and for Pocketsphinx
you'll need pulseaudio, swig, libasound2-dev, and libpulse-dev under Ubuntu.

Train the yolov3 neural network to improve image recognition

Installation
------------

.. code:: shell

   $ pip install goodbyecaptcha

Configuration
-------------

Please edit goodbyecaptcha.example.yaml and save as goodbyecaptcha.yaml

Usage
-----

If you want to use it in your own script

.. code:: python

    from goodbyecaptcha.solver import Solver

    pageurl = "https://www.google.com/recaptcha/api2/demo"
    sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

    proxy = "127.0.0.1:1000"
    auth_details = {"username": "user", "password": "pass"}
    method = 'images'  # 'audio'
    args = ["--timeout 5"]
    options = {"ignoreHTTPSErrors": True, "method": method, "args": args}
    client = Solver(
        # With Proxy
        pageurl, sitekey, options=options, proxy=proxy, proxy_auth=auth_details
        # Without Proxy
        # pageurl, sitekey, options=options
    )

    solution = client.loop.run_until_complete(client.start())
    if solution:
        print(solution)

If you want to use events

.. code:: python

    from goodbyecaptcha.solver import Solver

    pageurl = "https://www.google.com/recaptcha/api2/demo"
    sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

    proxy = "127.0.0.1:1000"
    auth_details = {"username": "user", "password": "pass"}
    method = 'images'  # 'audio'
    args = ["--timeout 5"]
    options = {"ignoreHTTPSErrors": True, "method": method, "args": args}


    class MySolver(Solver):
        def __init__(self, pageurl, sitekey, loop=None, proxy=None, proxy_auth=None,
                     options=None, enable_injection=True, retain_source=True, **kwargs):
            super().__init__(pageurl, sitekey, loop=loop, proxy=proxy, proxy_auth=proxy_auth,
                             options=options, enable_injection=enable_injection, retain_source=retain_source, **kwargs)

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

