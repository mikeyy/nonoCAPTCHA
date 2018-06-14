nonoCAPTCHA
===========

An async Python library to automate solving ReCAPTCHA v2 by audio, using Microsoft Azure's Speech-to-Text API.

Preview
-------

Check out this presentation of the script in action!

![nonoCAPTCHA preview](https://raw.githubusercontent.com/mikeyy/nonoCAPTCHA/master/presentation.gif)

Requirements
------------

Python 3.6.5+

Installation
------------

```pip install -r requirements.txt
```

Configuration
-------------

Please edit config.example.py and save as config.py

Usage
-----

```python run.py
```

Don't forget to edit variable count for amount of threads to use!

Or you can use

```python app.py
```

And access http://localhost:5000/get?pageurl=PAGEURL&sitekey=SITEKEY

Replace PAGEURL and SITEKEY with the websites ReCAPTCHA details.

Public
------

This script was first featured on Reddit at [/r/Python](https://reddit.com/r/Python) - [see here](https://www.reddit.com/r/Python/comments/8oqp7v/hey_i_made_a_google_recaptcha_solver_bot_too/) for the thread. I've finally decided to release the script.