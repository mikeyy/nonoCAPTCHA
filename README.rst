.. image:: https://img.shields.io/pypi/v/goodbyecaptcha.svg
    :alt: PyPI
    :target: https://pypi.org/project/goodbyecaptcha/
.. image:: https://img.shields.io/pypi/pyversions/goodbyecaptcha.svg
    :alt: PyPI - Python Version
    :target: https://pypi.org/project/goodbyecaptcha/
.. image:: https://img.shields.io/sourceforge/dt/goodbyecatpcha.svg
    :alt: SourceForge - Downloads
    :target: https://sourceforge.net/projects/goodbyecatpcha/files/latest/download
.. image:: https://img.shields.io/pypi/l/goodbyecaptcha.svg
    :alt: PyPI - License
    :target: https://pypi.org/project/goodbyecaptcha/
.. image:: https://img.shields.io/pypi/status/goodbyecaptcha.svg
    :alt: PyPI - Status
    :target: https://pypi.org/project/goodbyecaptcha/

GoodByeCaptcha
==============

An async Python library to automate solving ReCAPTCHA v2 by images/audio using
Mozilla's DeepSpeech, PocketSphinx, Microsoft Azure’s, Wit.AI, Google Speech or
Amazon's Transcribe Speech-to-Text API. Also image recognition to detect
the object suggested in the captcha. Built with Pyppeteer for Chrome
automation framework and similarities to Puppeteer, PyDub for easily
converting MP3 files into WAV, aiohttp for async minimalistic web-server,
and Python’s built-in AsyncIO for convenience.

Disclaimer
----------

This project is for educational and research purposes only. Any actions
and/or activities related to the material contained on this GitHub
Repository is solely your responsibility. The misuse of the information
in this GitHub Repository can result in criminal charges brought against
the persons in question. The author will not be held responsible in the
event any criminal charges be brought against any individuals misusing
the information in this GitHub Repository to break the law.

Compatibility
-------------

Linux, macOS, and Windows!

Requirements
------------

Python
`3.7 <https://www.python.org/downloads/release/python-370/>`__,
`FFmpeg <https://ffmpeg.org/download.html>`__, a `Microsoft
Azure <https://portal.azure.com/>`__ account for Bing Speech API access, an
Amazon Web Services account for Transcribe and S3 access, a Wit.AI or for Pocketsphinx.
You'll need pulseaudio, swig, libasound2-dev, and libpulse-dev under Debian.

Train the yolov3 neural network to improve image recognition.


Training YoloV3
---------------

I recommend training yolov3 to improve the recaptcha resolution with the following information:
 - `Dataset <https://storage.googleapis.com/openimages/web/download.html>`__
 - `Tutorial Video <https://www.youtube.com/playlist?list=PLZBN9cDu0MSk4IFFnTOIDihvhnHWhAa8W>`__
 - Object classes: `bicycle, bridge, bus, car, chimneys, crosswalk, fire hydrant, motorcycle, palm trees, parking meters, stair, taxis, tractors, traffic light, trees`


Installation
------------

.. code:: shell

   $ apt-get update && apt-get install -y libpangocairo-1.0-0 libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxtst6 libnss3 libcups2 libxss1 libxrandr2 libgconf-2-4 libasound2 libasound2-dev libatk1.0-0 libgtk-3-0 gconf-service libappindicator1 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgdk-pixbuf2.0-0 libglib2.0-0 libnspr4 libpango-1.0-0 libpulse-dev libstdc++6 libx11-6 libxcb1 libxext6 libxfixes3 libxrender1 libxtst6 ca-certificates fonts-liberation lsb-release xdg-utils build-essential ffmpeg swig software-properties-common curl python3-pocketsphinx
   $ pip install goodbyecaptcha

Install tutorial
----------------

.. image:: https://img.youtube.com/vi/hPYMUdQ2aV8/0.jpg
   :target: https://www.youtube.com/watch?v=hPYMUdQ2aV8

Configuration
-------------

Please edit goodbyecaptcha.example.yaml and save as goodbyecaptcha.yaml

Usage
-----

If you want to use it in your own script

.. code:: python

    from goodbyecaptcha.solver import Solver

    pageurl = "https://www.google.com/recaptcha/api2/demo"

    proxy = "127.0.0.1:1000"
    auth_details = {"username": "user", "password": "pass"}
    args = ["--timeout 5"]
    options = {"ignoreHTTPSErrors": True, "args": args}  # References: https://miyakogi.github.io/pyppeteer/reference.html
    client = Solver(
        # With Proxy
        # pageurl, lang='en-US', options=options, proxy=proxy, proxy_auth=auth_details
        # Without Proxy
        pageurl, lang='en-US', options=options
    )

    solution = client.loop.run_until_complete(client.start())
    if solution:
        print(solution)

If you want to use events

.. code:: python

    from goodbyecaptcha.solver import Solver

    pageurl = "https://www.google.com/recaptcha/api2/demo"

    proxy = "127.0.0.1:1000"
    auth_details = {"username": "user", "password": "pass"}
    args = ["--timeout 5"]
    options = {"ignoreHTTPSErrors": True, "args": args}  # References: https://miyakogi.github.io/pyppeteer/reference.html


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
        # pageurl, lang='en-US', options=options, proxy=proxy, proxy_auth=auth_details
        # Without Proxy
        pageurl, lang='en-US', options=options
    )

    client.loop.run_until_complete(client.start())
