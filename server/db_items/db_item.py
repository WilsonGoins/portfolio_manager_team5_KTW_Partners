from abc import ABC, abstactmethod
from typing import Self


class ADataBaseItem(ABC):

    @classmethod
    @abstactmethod
    def from_dict(cls, class_as_dict: dict) -> Self:
        """Convert DB row into python object."""
        pass

    @abstactmethod
    def to_dict(self):
        """Serialize python object to dict."""
        pass
