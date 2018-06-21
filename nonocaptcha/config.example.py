#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Configuration settings for Solver module

   Please edit "pagurl" and "sitekey" with the reCAPTCHA you are trying to
   solve.
   
   Edit proxy_source with the URL/file of your proxies
   
   Check this page for more details:
   https://2captcha.com/2captcha-api#solving_recaptchav2_new

   Should work with the configured values unless your proxies are really slow.

   I wouldn't touch data files, unless you're crazy.
"""

from nonocaptcha import __package_dir__ as package_dir

settings = {
    "debug": True,  # Prints actions as they occur, in your console
    "headless": False,  # Run browser headlessly
    "keyboard_traverse": False,  # Tab/Enter clicking of buttons instead
    "check_blacklist": False,  # Check Google search page for unusual traffic
                               # text and close on true before solving
    "api_subkey": "",  # API key for Azure Cognitive Services
    "pageurl": "https://google.com/recaptcha/api2/demo",  # ReCAPTCHA pageurl
    "sitekey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",  # ReCAPTCHA sitekey
    "proxy_source": "",  # Only used for app.py or run.py
    "gmail": "",  # Leave blank to ignore
    "gmail_password": "",  # Signing into google increases probability of success

    "data_files": {
        "override_js": f"{package_dir}/data/override.js",  # Used to override navigator
        "deface_html": f"{package_dir}/data/deface.html",  # HTML code to deface page
        "resolutions_json": f"{package_dir}/data/resolutions.json",  # Monitor resolutions
        "cookies": f"{package_dir}/data/cookie_jar"  # Stores cookies
    },
    "wait_timeout": {
        "load_timeout": 30,  # Seconds to wait for page to load
        "deface_timeout": 30,  # Seconds to wait for page to be defaced
        "success_timeout": 5,  # Seconds to wait due to checkbox animation
        "audio_button_timeout": 10,  # Seconds to wait for audio button
        "audio_link_timeout": 10,  # Seconds to wait for the audio link,
        # not the download!
        "reload_timeout": 10,  # Seconds to wait for audio reload
    },
}
