History
=======
### Current Version (2018-12-25)
* Implement working circumvention around detection
* Add option to enable/disable deface
* Add option to retain content of original page source
* Add Pyppeteer 0.0.25 to requirements

### Version 1.8.8 (2018-09-14)
* Add Pyppeteer 0.0.24 to requirements

### Version 1.8.7 (2018-09-14)
* Bug fix

### Version 1.8.6 (2018-09-14)
* Remove Websocket debugger

### Version 1.8.5 (2018-09-14)
* Output errors using traceback during solver initialization

### Version 1.8.4 (2018-09-14)
* Output errors during solver initialization
* Catch additional errors during page load
* Revert back to opening new tab

### Version 1.8.3 (2018-09-10)
* Add option to block images by setting block_images in configuration file.
* Return result to logging, for example "Result: Success", "Result: Blocked"
* Some behind the scene changes.

### Version 1.8.2 (2018-09-05)
* requirements.txt
    * Update to include Pyppeteer v0.0.21 (Whoops)

### Version 1.8.1 (2018-09-05)
* Move exceptions to a separate module - exceptions.py
* solver.py
    * Place some long running coroutines into AbastractEventLoop.create_task
    * No longer handling BaseExceptions on initial solve method
* launcher.py
  * Add modifications for Pyppeteer v0.0.21
* proxy.py
  * Replace asyncio.Lock with threading.Lock
* examples/
    * aiohttp_executor.py
        * Polished multithreading, ensuring browser exits (hopefully)
* Once again might have forgot something...

### Version 1.8.0 (2018-08-06)
* solver.py
    * Add function cleanup() to solver for closing browsers
    * Bypass Content-Security-Policy in response headers
* launcher.py
  * Remove signal handlers in launcher due to redundancy
* proxy.py
  * Remove last_used_timeout argument
* examples/
    * Change naming of files
    * api.py
        * Add multi-threaded support
* Fix bugs
* I might have forgot a change...

### Version 1.7.11 (2018-07-25)
* Add compatiblity for Python versions 3.6.0 - 3.7.0

### Version 1.7.10 (2018-07-18)
* Fix bug

### Version 1.7.9 (2018-07-17)
* Move configuration checking out of __init__.py into base.py

### Version 1.7.8 (2018-07-17)
* Remove proxy settings from configuration file
* Remove proxy protocol attribute from Solver (Aiohttp only supports HTTP)
* Fix proxy authentication when downloading audio file
* Add flake8 for auto-testing in repository

### Version 1.7.7 (2018-07-10)
* Fix new Chromium update with Pyppeteer 0.0.19

### Version 1.7.6 (2018-07-10)
* Fix check_detection timeout

### Version 1.7.5 (2018-07-10)
* Fix importing of non-existent/removed Exceptions

### Version 1.7.4 (2018-07-08)
* Change the way results are handled
    * Success will return in dict {'status': 'success', 'code': CAPTCHACODE}
    * Detected will return in dict {'status': 'detected'}
    * Max audio retries will return in dict {'status': 'retries_exceeded'}
* Set audio garabage removal to /3.1
* Add browser hang patches from Pyppeteer's repo

### Version 1.7.3 (2018-07-08)
* Fix nonocaptcha.example.yaml keys

### Version 1.7.2 (2018-07-08)
* Remove APSW dependency in Proxy database for Windows compatibility

### Version 1.7.1 (2018-07-08)
* Fix nonocaptcha.example.yaml inclusion

### Version 1.7.0 (2018-07-08)
* Add proxy management
    * example usage is provided in examples/run.py
* solver.py & audio.py
    * Add comments line by line
* Fix bugs

### Version 1.6.0 (2018-07-04)
* Switch configuration file to YAML format
* Clean-up requirements.txt
* Downgrade back to pyppeteer 0.0.17 due to frame issues

### Version 1.5.8 (2018-07-04)
* Fix bugs
* Update requirements

### Version 1.5.7 (2018-07-03)
* Fix bugs

### Version 1.5.6 (2018-07-03)
* speech.py
    * Remove playback left behind from debugging

### Version 1.5.5 (2018-07-03)
* audio.py
    * Fix change from InvalidDownload to DownloadError

### Verison 1.5.4 (2018-07-03)
* solver.py
    * Fix typo on DefaceError

### Verison 1.5.3 (2018-07-03)
* Fix bugs

### Verison 1.5.2 (2018-07-03)
* requirements.txt
    * Remove deepspeech since it makes Windows install fail

### Verison 1.5.1 (2018-07-03)
* solver.py
    * Revert back to documentloaded
    * Don't open a new tab

### Verison 1.5.0 (2018-07-02)
* Add support for Mozilla's DeepSpeech
* solver.py
    * Deface as soon as page loads except instead waiting for document
* Fix bugs

### Verison 1.4.23 (2018-07-02)
* Made more adjustments to the way exits are handled
* Resolutions.json is deprecated, update your configs
* solver.py
    * Removed OK| before the reCAPTCHA solution
* data/
    * Update deface.html with nonoCAPTCHA title

### Verison 1.4.22 (2018-07-02)
* launcher.py
    * Fix Exception thrown while killing non-existent process

### Verison 1.4.22 (2018-07-02)
* launcher.py
    * Fix typo in kill process

### Verison 1.4.21 (2018-07-02)
* Fix bugs

### Verison 1.4.19 (2018-07-02)
* speech.py
    * Fix mp3_to_wav()

### Verison 1.4.18 (2018-07-02)
* Add requests to requirements.txt

### Verison 1.4.17 (2018-07-02)
* Increase polling to 500ms for detection checking
* Recursively kill child processes of Chrome

### Verison 1.4.16 (2018-07-01)
* Fix audio downloading and file saving in Windows
* Pipe PocketSphinx logs to NUL under Windows
* Decrease polling to 100ms for detection checking

### Version 1.4.15 (2018-07-01)
* Attempt to fix issues with ongoing issue with Windows directory removal
* Possible fix for rare hanging on close
* More redifinition of exception handling

### Version 1.4.14 (2018-07-01)
* Redefine names of thrown exceptions better suited for invidual cases
* Fix bugs

### Version 1.4.13 (2018-06-30)
* Fix issues with Windows directory removal

### Version 1.4.12 (2018-06-30)
* Remove remove_readonly

### Version 1.4.11 (2018-06-30)
* Place subprocess into list for killing parent Chrome

### Version 1.4.10 (2018-06-30)
* Actually 'import subprocess'

### Version 1.4.9 (2018-06-30)
* launcher..py
    * 'import subprocess'

### Version 1.4.8 (2018-06-30)
* Kill parent Chromium process in Windows to allow deletion of Temporary User Data
* Fix Google login
* audio.py
    * Add 'import asyncio'
* solver.py
    * remove self.kill_chrome
* Fix bugs

### Version 1.4.7 (2018-06-30)
* Fix bugs

### Version 1.4.6 (2018-06-30)
* util.py
    * Fix aiohttp missing Timeout outside it's scope
* examples/app.py
    * Now uses aiohttp instead of Quart

### Version 1.4.5 (2018-06-29)
* Sphinx module
    * Strip static by percentage instead of 1500ms
* Audio solving
    * Fix "Please solve more" bug, where it would exit instead of trying again

### Version 1.4.4 (2018-06-29)
* Sphinx module
    * Strip static from audio files
    * Remove extra spaces from middle of words

### Version 1.4.3 (2018-06-29)
* Sphinx module
    * Remove detect silence

### Version 1.4.2 (2018-06-29)
* Fix bugs

### Version 1.4.1 (2018-06-29)
* Remove yet another print..

### Version 1.4.0 (2018-06-29)
* Add support for PocketSphinx

### Version 1.3.3 (2018-06-29)
* Actually remove a print function..

### Version 1.3.2 (2018-06-29)
* Remove a print function..

### Version 1.3.1 (2018-06-29)
* Fix Azure Speech-to-text

### Version 1.3.0 (2018-06-28)
* Add support for Amazon's Transcribe Speech-to-text

### Version 1.2.10 (2018-06-28)
* Fix bugs

### Version 1.2.9 (2018-06-27)
* Delete temporary Chrome profile on Browser exit

### Version 1.2.8 (2018-06-27)
* Possible fix for Chrome termination on ungraceful exit (such as timeout)

### Version 1.2.7 (2018-06-27)
* Revert back to old reCAPTCHA loading method

### Version 1.2.6 (2018-06-26)
* Remove chrome arguments uncertatin of their purpose
* Remove hardcoded timeout from solver, handle externally
* Add new example for HTTP client - create_task / get_task

### Version 1.2.5 (2018-06-26)
* Fix bugs

### Version 1.2.4 (2018-06-26)
* Timeout patch in solver reverted

### Version 1.2.3 (2018-06-25)
* Add CHANGES.md file
* Add TODO.md file
* Lower mouse click (30ms,130ms) and wait delay(500ms,1.5secs)

### ... unfinished

### Version 0.0.14 (2018-06-20)
* Fix bugs

### Version 0.0.13 (2018-06-20)
* Fix bugs

### Version 0.0.12 (2018-06-20)
* nonocaptcha/util.py
    * Increase get_page default timeout to 5 minutes
* Add config.py missing warning
* Fix bugs

### Version 0.0.11 (2018-06-20)
* Fix bugs

### Version 0.0.10 (2018-06-20)

* data/
    * Move to package directory
* examples/
    * app.py
        * Proxies load in packground with 10 minute interval
* setup.py
    * Add Github url
* Rename package to be all lowercase
* Register PyPI
* Keep count of tasks in logging
* Fix bugs

### Version 0.0.9 (2018-06-20)

* data/
    * Add cookie_jar directory
* config.py to work from current directory
* Add new presentation
* Option to sign-in to single Google account
* Fix bugs

### Version 0.0.6 (2018-06-19)

* Distribution
    * Script can now be installed with setup.py
* config.example.py
    * Blacklist setting added
* examples/
    * run.py
        * Parallel continous browsing
* Log use logging module
* Async subprocess calls browser
* Add Extra chrome arguments  for less tracking
* Option to check Google search for blacklist heuristic
* Fix bugs

### Version 0.0.3 (2018-06-17)

* README.md
    * Added Compatibility section
    * Updated Requirements to include FFmpeg
* config.example.py
    * Added debug setting
    * Lowered success_timeout to 5 seconds

### Version 0.0.2 (2018-06-15)

* README.md
    * Added Displaimer section
    * Added presentation GIF
* Code formatting with black


### Version 0.0.1 (2018-06-14)

* Released to Githib
