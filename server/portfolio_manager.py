from finance_manager import FinanceManager
from db_manager import DBManager
from datetime import datetime
from db_items import Holding, Transaction


class PortfolioManager:
    """This class is responsible for handling all portfolio related queries. It delegates to DBManager and FinanceManager as needed"""

    def __init__(self, db_manager: DBManager, finance_manager: FinanceManager, cash_value: float):
        self.db_manager = db_manager
        self.finance_manager = finance_manager

        # start user with a cash value
        self.db_manager.add_holding(
            Holding("cash_value", "Cash", "Cash", cash_value))

    # Retrieves all data needed for overview page
    # Returns in a dict of form
        # {HoldingsTable: [{symbol: AAPL, ..., market_value: ..., change_since_close: ..., allocation_pct: 12.5}, {symbol: NVDA, ...}],
        #  AllocationsDict: {etf: 40, cash: 60}
        # }

    def GetOverviewData(self):
        finalRes = {}
        # first we get the data on holdings and structure it for the holdings table
        # this is a list of Holding objects, each with {ticker, name, h_type, quantity_shares, ...}
        dbHoldingsRes = self.db_manager.get_holdings()

        holdingsWithPrice = []
        for holding in dbHoldingsRes:      # this will iterate through the list we got and add current price for each of them
            if (holding.ticker == "cash_value"):
                continue
            yahooRes = self.finance_manager.get_stock_by_ticker(holding.ticker)
            if (yahooRes is None):
                raise ValueError("Holding must be a valid security.")
            holdingsWithPrice.append({"symbol": holding.ticker, "name": holding.name, "h_type": holding.h_type,
                                      "num_shares": holding.quantity_shares, "curr_price": yahooRes["current_price"], "previous_close": yahooRes["previous_close"]})

        # now clean up the data to have all the necessary information (cash is folded in as its own holding)
        enrichedHoldings = self.CalculateHoldingInfo(holdingsWithPrice)
        finalRes["HoldingsTable"] = enrichedHoldings

        # now get the allocations for the allocations graph
        allocationsDict = self.CalculateAllocationByType(
            enrichedHoldings)       # cash is passed in as a holding here
        finalRes["AllocationsDict"] = allocationsDict

        return finalRes

    # Retrieves all transactions from database
    # returns a list of transaction dicts with the date, ticker, quantity,
    # price, and action taken for each transaction

    def GetTransactions(self):
        finalRes = []
        dbTransRes = self.db_manager.get_transactions()
        for trans in dbTransRes:
            # format data...
            finalRes.append({
                "date": trans.trans_date,
                "ticker": trans.ticker,
                "quantity": trans.quantity,
                "price": trans.price,
                "action": trans.action_taken
            })
        return finalRes

    # Buy shares of a security. Deducts the cost from cash, updates the holding, and records the transaction.

    def Buy(self, ticker: str, quantity: int, price: float):
        if quantity <= 0:
            raise ValueError("quantity must be a positive number of shares")

        total_cost = quantity * price
        cash = self.GetCashAmount()
        if total_cost > cash:
            raise ValueError("insufficient cash to complete this purchase")

        # add to the existing position, or open a new one if we don't hold it yet
        existing = self.db_manager.get_holding(
            ticker)      # get holding if it exists
        if existing is None:
            yahooData = self.finance_manager.get_stock_by_ticker(ticker)
            if (yahooData is None):
                raise ValueError("Holding must be a valid security.")
            self.db_manager.add_holding(
                Holding(ticker, yahooData["name"], yahooData["stock_type"], quantity))
        else:
            existing.quantity_shares += quantity
            self.db_manager.update_holding(existing)

        # TODO: this updates the user's cash holding, need to confirm that this is how we want this done
        self.db_manager.update_holding(
            Holding("cash_value", "Cash", "Cash", (cash - total_cost)))

        # record the buy in the transactions ledger
        self.db_manager.add_transaction(Transaction(None, ticker, quantity, price, datetime.now(
            # TODO: passing in None for now (bc trans_id is still required)
        ), "buy"))

    # Sell shares of a security.
    # Adds the proceeds to cash, reduces (or closes) the holding, and records the transaction.

    def Sell(self, ticker: str, quantity: int, price: float):
        if quantity <= 0:
            raise ValueError("quantity must be a positive number of shares")

        existing = self.db_manager.get_holding(ticker)
        if existing is None or existing.quantity_shares < quantity:
            raise ValueError("cannot sell more shares than are currently held")

        cash = self.GetCashAmount()

        sellAmount = quantity * price

        # TODO: this updates the user's cash holding, need to confirm that this is how we want this done
        self.db_manager.update_holding(
            Holding("cash_value", "Cash", "Cash", (cash + sellAmount)))

        existing.quantity_shares -= quantity
        if existing.quantity_shares == 0:
            self.db_manager.delete_holding(existing)
        else:
            self.db_manager.update_holding(existing)

        # record the sell in the transactions ledger
        self.db_manager.add_transaction(Transaction(None, ticker, quantity, price, datetime.now(
            # TODO: passing in None for now (bc trans_id is still required)
        ), "sell"))

    # Gets the current amount of cash for the user
    # Returns the amount of cash, not the cash holding

    def GetCashAmount(self) -> float:
        dbRes = self.db_manager.get_cash()
        if (dbRes):
            return dbRes
        else:
            return 0

    # Returns a list of holdings dicts with all the same fields, plus the market value,
    # the dollar change since yesterday's close, and each holding's % allocation of the portfolio.
    # Cash is included as its own holding (h_type "Cash") whose market value is the portfolio's
    # cash balance; fields that don't apply to cash (symbol, num_shares, curr_price, last_close,
    # change_since_close) are set to "na". Cash is part of the total used for % allocation.

    def CalculateHoldingInfo(self, holdings):
        enriched = []
        cashAmount = self.GetCashAmount()   # gets the cash amount we currently have
        total_value = cashAmount

        for holding in holdings:
            num_shares = holding["num_shares"]
            curr_price = holding["curr_price"]
            previous_close = holding["previous_close"]

            market_value = num_shares * curr_price
            change_since_close = num_shares * (curr_price - previous_close)
            total_value += market_value

            enriched.append({
                "symbol": holding["symbol"],
                "name": holding["name"],
                "h_type": holding["h_type"],
                "num_shares": num_shares,
                "curr_price": curr_price,
                "previous_close": previous_close,
                "market_value": market_value,
                "change_since_close": change_since_close,
            })

        # add cash as a holding, with "--" for the fields that don't apply to it
        enriched.append({
            "symbol": "cash_value",
            "name": "Cash",
            "h_type": "Cash",
            "num_shares": "--",
            "curr_price": "--",
            "previous_close": "--",
            # TODO: we probably want to display the cash amount in the 'market_value' field, so even though we may internally represent it as num_shares, is this good?
            "market_value": cashAmount,
            "change_since_close": "--",
        })

        # second pass: now that we know the portfolio total (holdings + cash), set each holding's % allocation
        for holding in enriched:
            holding["allocation_pct"] = (
                holding["market_value"] / total_value * 100) if total_value else 0

        return enriched

    # Aggregates market value of holdings by type (cash is included as the "cash" type,
    # since CalculateHoldingInfo adds it as a holding)
    # Returns a dict of {h_type: percentage_of_portfolio}

    def CalculateAllocationByType(self, holdings):
        value_by_type = {}
        total_value = 0

        for holding in holdings:
            h_type = holding["h_type"]
            market_value = holding.get(
                "market_value", holding["num_shares"] * holding["curr_price"])

            value_by_type[h_type] = value_by_type.get(h_type, 0) + market_value
            total_value += market_value

        allocation = {}
        for h_type, value in value_by_type.items():
            allocation[h_type] = (value / total_value *
                                  100) if total_value else 0

        return allocation
