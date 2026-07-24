from .db_item import ADataBaseItem
from typing import Self


class Holding(ADataBaseItem):

    def __init__(
        self,
        ticker: str,
        name: str,
        h_type: str,
        quantity_shares: int,
        current_price: float,
        market_value: float,
        change_today: float,
        gain_loss: float,
        allocation_percentage: float
    ):
        self.ticker = ticker
        self.name = name
        self.h_type = h_type
        self.quantity_shares = quantity_shares
        self.current_price = current_price
        self.market_value = market_value
        self.change_today = change_today
        self.gain_loss = gain_loss
        self.allocation_percentage = allocation_percentage

    @classmethod
    def from_dict(cls, class_as_dict: dict) -> Self:
        return cls(
            ticker=class_as_dict["ticker"],
            name=class_as_dict["name"],
            h_type=class_as_dict["h_type"],
            quantity_shares=class_as_dict["quantity_shares"],
            current_price=class_as_dict["current_price"],
            market_value=class_as_dict["market_value"],
            change_today=class_as_dict["change_today"],
            gain_loss=class_as_dict["gain_loss"],
            allocation_percentage=class_as_dict["allocation_percentage"],
        )

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "h_type": self.h_type,
            "quantity_shares": self.quantity_shares,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "change_today": self.change_today,
            "gain_loss": self.gain_loss,
            "allocation_percentage": self.allocation_percentage,
        }
