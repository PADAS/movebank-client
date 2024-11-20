

class MBClientError(Exception):
    pass


class MBValidationError(MBClientError):
    pass


class MBForbiddenError(MBClientError):
    pass


# ToDo: Add more custom errors as we discover them.
