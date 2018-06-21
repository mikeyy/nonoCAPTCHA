nonoCAPTCHA
===========

An async Python library to automate solving ReCAPTCHA v2 by audio, using
Microsoft Azure’s Speech-to-Text API. Built with Pyppeteer for it’s
Chrome automation framework and similarities to Puppeteer, PyDub for
easily converting MP3 files into WAV, Quart for it’s async minimalist
web-framework, and Python’s built-in AsyncIO for convenience.

Disclaimer
----------

This project is for educational and research purposes only. Any actions
and or activities related to the material contained on this GitHub
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

Check out this 1-minute presentation of the script in action, with only
8 threads!

.. figure:: https://github.com/mikeyy/nonoCAPTCHA/blob/presentation/presentation.gif
   :alt: nonoCAPTCHA preview

   nonoCAPTCHA preview

Compatibility
-------------

Linux, macOS, and Windows!

Requirements
------------

`Python
3.6.5+ <https://www.python.org/downloads/release/python-365/>`__,
`FFmpeg <https://ffmpeg.org/download.html>`__ and a `Microsoft
Azure <https://portal.azure.com/>`__ account with Bing Speech API access

Installation
------------

.. code:: shell

   $ pip install nonocaptcha

Configuration
-------------

Please edit config.example.py and save as config.py

Usage
-----

If you would like to use it in your own script

.. code:: python

   from nonocaptcha.solver import Solver
   from config import settings

   client = Solver(
       settings['pageurl'],
       settings['sitekey'],
       options=options,
       proxy=proxy,
       proxy_auth=auth_details(),
   )

   answer = await client.start()
   if answer:
       print(answer)

Use the included multithread script.

*Edit variable count for amount of threads to use*

.. code:: shell

   $ python examples/run.py

Use the included mini-server and access
http://localhost:5000/get?pageurl=PAGEURL&sitekey=SITEKEY

*Replace PAGEURL and SITEKEY with the websites ReCAPTCHA details.*

.. code:: shell

   $ python examples/app.py
