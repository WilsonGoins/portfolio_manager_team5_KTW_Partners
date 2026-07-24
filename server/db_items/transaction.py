from datetime import datetime
from typing import Self
from db_item import ADataBaseItem


class Transaction(ADataBaseItem):

    def __init__(
        self,
        trans_id: int,
        ticker: str,
        quantity: int,
        price: float,
        trans_date: datetime,
        action_taken: str,
    ):
        self.trans_id = trans_id
        self.ticker = ticker
        self.quantity = quantity
        self.price = price
        self.trans_date = trans_date
        self.action_taken = action_taken

    @classmethod
    def from_dict(cls, class_as_dict: dict) -> Self:
        return cls(
            trans_id=class_as_dict["trans_id"],
            ticker=class_as_dict["ticker"],
            quantity=class_as_dict["quantity"],
            price=class_as_dict["price"],
            trans_date=class_as_dict["trans_date"],
            action_taken=class_as_dict["action_taken"],
        )

    def to_dict(self) -> dict:
        return {
            "trans_id": self.trans_id,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "price": self.price,
            "trans_date": self.trans_date,
            "action_taken": self.action_taken,
        }
