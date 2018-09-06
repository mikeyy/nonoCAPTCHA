"""Exceptions used in library"""


class SafePassage(Exception):
    """ Raised when all checks have passed. Such as being detected or try
    again.
    """
    pass


class TryAgain(Exception):
    """ Raised when audio deciphering is incorrect and we can try again. """
    pass


class ReloadError(Exception):
    """ Raised when audio file doesn't reload to a new one. """
    pass


class DownloadError(Exception):
    """ Raised when downloading the audio file errors. """
    pass


class ButtonError(Exception):
    """ Raised when a button doesn't appear. """
    pass


class DefaceError(Exception):
    """ Raised when defacing page times out. """
    pass


class PageError(Exception):
    """ Raised when loading page times out. """
    pass
