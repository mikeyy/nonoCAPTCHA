TODO
=======

* Add type casing
* Rewrite the library for optimal asynchronicity and better readability, while 
reflecting standard coding practice e.g.
    * Accept user-defined loop
    * Assign expensive(slow) operations as a Task, rather than awaiting
    * Locate blocking synchronized operations
    * Determine practical solution for Timeout usage, reducing Exceptions
    * Possibly remove certain speech-to-text services
    * Research other speech-to-text services for implementation
    * And more
* Find and fix nasty bugs that appear under certain circumstances, e.g.
    * A browser signaled to terminate raises an IncompleteReadError exception,
      one out of 100 instances.
* Complete unfinished work in the repo
* Review and formulate working comprehensive examples
* Scrutinize the repo in unison for areas insisting improvement
* And more...
