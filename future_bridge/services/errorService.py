# ------------------------------


# ------------------------------
# Errors
# ------------------------------
from future_bridge.config.messages import ErrorMessages


class UserNotFound(Exception):
    """
    Exception raised when a user is not found in the DB.
    """

    def __init__(self, username=None, message=ErrorMessages.ERROR_NOT_FOUND):
        self.username = username
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.username}'


class UserAlreadyExistsError(Exception):
    """
    Exception raised when trying to add a user that already exists in the database.
    """

    def __init__(self, username, message=ErrorMessages.ERROR_USER_EXIST):
        self.username = username
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.username}'

# ------------------------------


