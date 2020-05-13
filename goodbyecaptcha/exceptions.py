#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Exceptions used in library. """


class goodbyecaptchaError(Exception):
    """ GoodByeCAPTCHA base exception. """


class SafePassage(goodbyecaptchaError):
    """ Raised when all checks have passed. Such as being detected or try again. """
    pass


class ResolveMoreLater(goodbyecaptchaError):
    """ Raised when audio deciphering is incorrect and we can try again. """
    pass


class TryAgain(goodbyecaptchaError):
    """ Raised when audio deciphering is incorrect and we can try again. """
    pass


class ReloadError(goodbyecaptchaError):
    """ Raised when audio file doesn't reload to a new one. """
    pass


class DownloadError(goodbyecaptchaError):
    """ Raised when downloading the audio file errors. """
    pass


class ButtonError(goodbyecaptchaError):
    """ Raised when a button doesn't appear. """
    pass


class IframeError(goodbyecaptchaError):
    """ Raised when defacing page times out. """
    pass
