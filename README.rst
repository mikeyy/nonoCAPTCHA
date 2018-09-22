.. image:: https://travis-ci.org/mikeyy/nonoCAPTCHA.svg?branch=master
    :target: https://travis-ci.org/mikeyy/nonoCAPTCHA
.. image:: https://img.shields.io/pypi/v/nonocaptcha.svg
    :alt: PyPI
    :target: https://pypi.org/project/nonocaptcha/
.. image:: https://img.shields.io/pypi/pyversions/nonocaptcha.svg
    :alt: PyPI - Python Version
    :target: https://pypi.org/project/nonocaptcha/
.. image:: https://img.shields.io/pypi/l/nonocaptcha.svg
    :alt: PyPI - License   
    :target: https://pypi.org/project/nonocaptcha/
.. image:: https://img.shields.io/pypi/status/nonocaptcha.svg
    :alt: PyPI - Status
    :target: https://pypi.org/project/nonocaptcha/

nonoCAPTCHA
===========

An async Python library to automate solving ReCAPTCHA v2 by audio using
Mozilla's DeepSpeech, PocketSphinx, Microsoft Azure’s, and Amazon's Transcribe 
Speech-to-Text API. Built with Pyppeteer for Chrome automation framework
and similarities to Puppeteer, PyDub for easily converting MP3 files into WAV, 
aiohttp for async minimalistic web-server, and Python’s built-in AsyncIO
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

Public
------

This script was first featured on Reddit at
`/r/Python <https://reddit.com/r/Python>`__ - `see
here <https://www.reddit.com/r/Python/comments/8oqp7v/hey_i_made_a_google_recaptcha_solver_bot_too/>`__
for the thread. I’ve finally decided to release the script.

Preview
-------

Check out 1-minute presentation of the script in action, with only
8 threads!

.. figure:: https://github.com/mikeyy/nonoCAPTCHA/blob/presentation/presentation.gif
   :alt: nonoCAPTCHA preview

Compatibility
-------------

Linux, macOS, and Windows!

Requirements
------------

Python
`3.6.0 <https://www.python.org/downloads/release/python-360/>`__ -
`3.7.0 <https://www.python.org/downloads/release/python-370/>`__,
`FFmpeg <https://ffmpeg.org/download.html>`__, a `Microsoft
Azure <https://portal.azure.com/>`__ account for Bing Speech API access, an
Amazon Web Services account for Transcribe and S3 access, and for Pocketsphinx
you'll need pulseaudio, swig, libasound2-dev, and libpulse-dev under Ubuntu.

Installation
------------

.. code:: shell

   $ pip install nonocaptcha

Configuration
-------------

Please edit nonocaptcha.example.yaml and save as nonocaptcha.yaml

Usage
-----

If you want to use it in your own script

.. code:: python

   import asyncio
   from nonocaptcha.solver import Solver

   pageurl = "https://www.google.com/recaptcha/api2/demo"
   sitekey = "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-"

   proxy = "127.0.0.1:1000"
   auth_details = {
        "username": "user",
        "password": "pass"
   }
   args = ["--timeout 5"]
   options = {"ignoreHTTPSErrors": True, "args": args}
   client = Solver(
        pageurl,
        sitekey,
        options=options,
        proxy=proxy,
        proxy_auth=auth_details,
   )

   solution = asyncio.get_event_loop().run_until_complete(client.start())
   if solution:
        print(solution)

Donations
---------

The use of proxies are required for my continuous updates and fixes on
nonoCAPTCHA. Any donations would be a great help in allowing me to purchase 
these proxies, that are clearly expensive. If anyone is willing to share
their proxies, I wouldn't hesitate to accept the offer.

Bitcoin: 1BfWQWAZBsSKCNQZgsq2vwaKxYvkrhb14u