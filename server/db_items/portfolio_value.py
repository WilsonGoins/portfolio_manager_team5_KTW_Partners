from datetime import datetime
from .db_item import ADataBaseItem
from typing import Self


class PortfolioValue(ADataBaseItem):
    def __init__(self, p_date: datetime, value: float):
        self.p_date = p_date
        self.value = value

    @classmethod
    def from_dict(cls, class_as_dict: dict) -> Self:
        return cls(p_date=class_as_dict["p_date"],
                   value=class_as_dict["value"])

    def to_dict(self) -> dict:
        return {
            "p_date": self.p_date,
            "value": self.value
        }
