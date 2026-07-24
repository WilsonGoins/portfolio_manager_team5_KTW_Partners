from abc import ABC, abstractmethod
from typing import Self


class ADataBaseItem(ABC):

    @classmethod
    @abstractmethod
    def from_dict(cls, class_as_dict: dict) -> Self:
        """Convert DB row into python object."""
        pass

    @abstractmethod
    def to_dict(self):
        """Serialize python object to dict."""
        pass
