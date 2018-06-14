#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Configuration settings for Solver module

   Please edit "pagurl" and "sitekey" with the reCAPTCHA you are trying to
   solve.
   
   Edit proxy_source with the URL/file of your proxies
   
   Check this page for more details:
   https://2captcha.com/2captcha-api#solving_recaptchav2_new

   Should work with the configured values unless your proxies are really slow.
"""

settings = {
    "api_subkey" = "", # API key for Azure Cognitive Services
    "pageurl": "https://www.google.com/recaptcha/api2/demo",
    "sitekey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
    "proxy_source": 
        "",
    "headless": False,
    "keyboard_traverse": False,

    "data_files": {
        "override_js": "data/override.js",
        "deface_html": "data/deface.html",
        "resolutions_json": "data/resolutions.json",
    },
    "wait_timeout": {
        "load_timeout": 30,  # Seconds to wait for page to load
        "deface_timeout": 30,  # Seconds to wait for page to be defaced
        "success_timeout": 15,  # Seconds to wait due to checkbox animation
        "audio_button_timeout": 10,  # Seconds to wait for audio button
        "audio_link_timeout": 10,  # Seconds to wait for the audio link,
                                   # not the download!
    },
}
