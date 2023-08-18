from enum import Enum


class TagDataOperations(str, Enum):
    ADD_DATA = "add-data"  # upload data file to Movebank

    def __str__(self) -> str:
        return self.value


class PermissionOperations(str, Enum):
    ADD_USER_PRIVILEGES = "add-user-privileges"  # Add access permissions without removing the existent ones
    UPDATE_USER_PRIVILEGES = "update-user-privileges"  # Replace all existing access permissions
    REMOVE_USER_PRIVILEGES = "remove-user-privileges"  # Remove access permissions

    def __str__(self) -> str:
        return self.value
