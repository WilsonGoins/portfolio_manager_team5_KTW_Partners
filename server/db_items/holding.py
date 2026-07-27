from .db_item import ADataBaseItem
from typing import Self


class Holding(ADataBaseItem):

    def __init__(
        self,
        ticker: str,
        name: str,
        h_type: str,
        quantity_shares: int,
    ):
        self.ticker = ticker
        self.name = name
        self.h_type = h_type
        self.quantity_shares = quantity_shares

    @classmethod
    def from_dict(cls, class_as_dict: dict) -> Self:
        return cls(
            ticker=class_as_dict["ticker"],
            name=class_as_dict["name"],
            h_type=class_as_dict["h_type"],
            quantity_shares=class_as_dict["quantity_shares"],
        )

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "h_type": self.h_type,
            "quantity_shares": self.quantity_shares,
        }
