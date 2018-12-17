#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Exceptions used in library. """


class nonocaptchaError(Exception):
    """ nonoCAPTCHA base exception. """


class SafePassage(nonocaptchaError):
    """ Raised when all checks have passed. Such as being detected or try
    again.
    """
    pass


class TryAgain(nonocaptchaError):
    """ Raised when audio deciphering is incorrect and we can try again. """
    pass


class ReloadError(nonocaptchaError):
    """ Raised when audio file doesn't reload to a new one. """
    pass


class DownloadError(nonocaptchaError):
    """ Raised when downloading the audio file errors. """
    pass


class ButtonError(nonocaptchaError):
    """ Raised when a button doesn't appear. """
    pass


class IframeError(nonocaptchaError):
    """ Raised when defacing page times out. """
    pass


class PageError(nonocaptchaError):
    """ Raised when loading page times out. """
    pass
