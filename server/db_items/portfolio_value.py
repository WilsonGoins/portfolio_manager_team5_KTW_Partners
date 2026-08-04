from datetime import datetime
from .db_item import ADataBaseItem
from typing import Self


class PortfolioValue(ADataBaseItem):
    def __init__(
        self, p_date: datetime, value: float, day_change: float, day_change_pct: float
    ):
        self.p_date = p_date
        self.value = value
        self.day_change = day_change
        self.day_change_pct = day_change_pct

    @classmethod
    def from_dict(cls, class_as_dict: dict) -> Self:
        return cls(
            p_date=class_as_dict["p_date"],
            value=class_as_dict["total_value"],
            day_change=class_as_dict["day_change"],
            day_change_pct=class_as_dict["day_change_pct"],
        )

    def to_dict(self) -> dict:
        return {
            "p_date": self.p_date,
            "total_value": self.value,
            "day_change": self.day_change,
            "day_change_pct": self.day_change_pct,
        }
