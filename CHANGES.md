History (Work in progress)
=======
### Current Version (2018-06-29)
* Sphinx module
    * Strip static by percentage instead of 1500ms
* Audio solving
    * Fix "Please solve more" bug, where it wouldn't exit instead of trying again

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
