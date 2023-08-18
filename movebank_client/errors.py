

class MBClientError(Exception):
    pass


class MBValidationError(MBClientError):
    pass


# ToDo: Add more custom errors as we discover them.
