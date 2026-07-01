"""AF55 exceptions."""
class Af55Error(Exception):
    """Base AF55 exception."""
class Af55CannotConnect(Af55Error):
    """Connection failed."""
class Af55AuthenticationError(Af55Error):
    """Authentication failed."""
class Af55ApiError(Af55Error):
    """API error."""
