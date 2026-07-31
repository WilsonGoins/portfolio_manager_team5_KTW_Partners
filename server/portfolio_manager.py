from finance_manager import FinanceManager
from db_manager import DBManager
from datetime import datetime
from db_items import Holding, Transaction


_CONSERVATIVE_BETA_CEILING = 0.8
_MARKET_BETA_CEILING = 1.2
_RISK_HIGHLIGHT_MIN_GAP_PCT = 3.0       # difference threshold between a holding's share of the risk and a holidng's share of the portfolio


class PortfolioManager:
    """This class is responsible for handling all portfolio related queries. It delegates to DBManager and FinanceManager as needed"""

    def __init__(self, db_manager: DBManager, finance_manager: FinanceManager):
        self.db_manager = db_manager
        self.finance_manager = finance_manager

    # Retrieves all data needed for overview page
    # Returns in a dict of form
        # {HoldingsTable: [{symbol: AAPL, ..., market_value: ..., change_since_close: ..., allocation_pct: 12.5}, {symbol: NVDA, ...}],
        #  Allocations: [{h_type: ETF, market_value: 46559.62, allocation_pct: 36.0}, {h_type: Cash, ...}],
        #  PortfolioSummary: {total_value: ..., day_change: ..., day_change_pct: ...},
        #  PortfolioHistory: [{date: "2026-07-27", value: ...}, ...],
        #  TopMovers: [{symbol: ..., name: ..., price: ..., change: ...}, ...],
        #  LastUpdated: "2026-07-30T10:20:00-04:00"
        # }

    def GetOverviewData(self):
        finalRes = {}
        # first we get the data on holdings and structure it for the holdings table
        # this is a list of Holding objects, each with {ticker, name, h_type, quantity_shares, ...}
        dbHoldingsRes = self.db_manager.get_holdings()

        # one batched lookup rather than a call per holding inside the loop below:
        # those calls used to run back to back, so the page waited on the sum of
        # every round trip. Batched, they overlap and cost about one round trip total.
        quotes = self.finance_manager.get_stocks_by_tickers(
            [holding.ticker for holding in dbHoldingsRes])

        holdingsWithPrice = []
        for holding in dbHoldingsRes:      # this will iterate through the list we got and add current price for each of them
            yahooRes = quotes.get(holding.ticker)
            if (yahooRes is None):
                raise ValueError("Holding must be a valid security.")
            holdingsWithPrice.append({"symbol": holding.ticker, "name": holding.name, "h_type": holding.h_type,
                                      "num_shares": holding.quantity_shares, "curr_price": yahooRes["current_price"], "previous_close": yahooRes["previous_close"]})

        # now clean up the data to have all the necessary information (cash is folded in as its own holding)
        enrichedHoldings = self.CalculateHoldingInfo(holdingsWithPrice)
        finalRes["HoldingsTable"] = enrichedHoldings

        # now get the allocations for the allocations graph
        allocations = self.CalculateAllocationByType(
            enrichedHoldings)       # cash is passed in as a holding here
        finalRes["Allocations"] = allocations

        # headline numbers for the portfolio value card
        summary = self.CalculatePortfolioSummary(enrichedHoldings)
        finalRes["PortfolioSummary"] = summary

        # the value chart's series: stored snapshots, capped with today's live
        # total so the line stays current between snapshot writes
        finalRes["PortfolioHistory"] = self.GetPortfolioHistory(
            todaysValue=summary["total_value"])

        # the watchlist's rows
        finalRes["TopMovers"] = self.GetTopMovers()

        # when the yahoo finance quotes above were pulled, so the UI can show how
        # stale the prices are. stamped last, once every quote is in hand.
        finalRes["LastUpdated"] = datetime.now().astimezone().isoformat()

        return finalRes

    # Today's biggest market movers for the watchlist. Reshapes the finance
    # manager's quotes into [{"symbol", "name", "price", "change"}], where
    # change is the percent move since the previous close.

    def GetTopMovers(self, count: int = 5):
        finalRes = []

        for mover in self.finance_manager.get_top_movers(count):
            price = mover["curr_price"]
            previousClose = mover["previous_close"]

            # skip any quote we can't compute a move from rather than
            # sending the frontend a null it has to defend against
            if price is None or not previousClose:
                continue

            finalRes.append({
                "symbol": mover["symbol"],
                "name": mover["name"],
                "price": price,
                "change": (price - previousClose) / previousClose * 100,
            })

        return finalRes

    # Returns the stored portfolio value snapshots oldest first, as
    # [{"date": "YYYY-MM-DD", "value": float}]. When todaysValue is given it is
    # appended as (or overwrites) today's point, so the series ends at the
    # portfolio's live value rather than at the last snapshot that was written.

    def GetPortfolioHistory(self, todaysValue: float = None):
        dbRes = self.db_manager.get_portfolio_values()

        history = []
        for pv in sorted(dbRes, key=lambda pv: pv.p_date):
            history.append({
                "date": pv.p_date.strftime("%Y-%m-%d"),
                # Decimal isn't JSON serializable
                "value": float(pv.value),
            })

        if todaysValue is not None:
            today = datetime.now().strftime("%Y-%m-%d")
            if history and history[-1]["date"] == today:
                history[-1]["value"] = todaysValue
            else:
                history.append({"date": today, "value": todaysValue})

        return history

    # Totals up the enriched holdings (cash included) into the headline numbers
    # for the portfolio value card: what the portfolio is worth right now, and
    # how much of that is today's movement in dollars and percent.

    def CalculatePortfolioSummary(self, holdings):
        total_value = sum(holding["market_value"] for holding in holdings)

        # cash carries "--" for change_since_close, so only total the real numbers
        day_change = sum(holding["change_since_close"] for holding in holdings
                         if isinstance(holding["change_since_close"], (int, float)))

        previous_value = total_value - day_change
        day_change_pct = (day_change / previous_value *
                          100) if previous_value else 0

        return {
            "total_value": total_value,
            "day_change": day_change,
            "day_change_pct": day_change_pct,
        }

    # Retrieves all transactions from database
    # returns a list of transaction dicts with the date, ticker, quantity,
    # price, and action taken for each transaction

    def GetTransactions(self):
        finalRes = []
        dbTransRes = self.db_manager.get_transactions()
        for trans in dbTransRes:
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

        # set cash to new amount after purchase
        self.db_manager.set_cash((cash - total_cost))

        # record the buy in the transactions ledger
        self.db_manager.add_transaction(Transaction(
            None, ticker, quantity, price, datetime.now(), "buy"))

    # Sell shares of a security.
    # Adds the proceeds to cash, reduces (or closes) the holding, and records the transaction.

    def Sell(self, ticker: str, quantity: int, price: float):
        if quantity <= 0:
            raise ValueError("quantity must be a positive number of shares")

        existing = self.db_manager.get_holding(ticker)
        if existing is None or existing.quantity_shares < quantity:
            raise ValueError("cannot sell more shares than are currently held")

        cash = self.GetCashAmount()         # get current amount of cash

        sellAmount = quantity * price       # get amount of money we make from sale

        # add that to current cash
        self.db_manager.set_cash((cash + sellAmount))

        existing.quantity_shares -= quantity
        if existing.quantity_shares == 0:
            self.db_manager.delete_holding(existing)
        else:
            self.db_manager.update_holding(existing)

        # record the sell in the transactions ledger
        self.db_manager.add_transaction(Transaction(
            None, ticker, quantity, price, datetime.now(), "sell"))

    # Gets the current amount of cash for the user
    # Returns the amount of cash, not the cash holding

    def GetCashAmount(self) -> float:
        dbRes = self.db_manager.get_cash()
        if (dbRes):
            return dbRes
        else:
            return 0

    # Returns a list of holdings dicts with all the same fields, plus the market value, the
    # change since yesterday's close as both dollars (change_since_close) and a percent
    # (change_pct_since_close), and each holding's % allocation of the portfolio.
    # Cash is included as its own holding (h_type "Cash") whose market value is the portfolio's
    # cash balance; fields that don't apply to cash (symbol, num_shares, curr_price, last_close,
    # change_since_close, change_pct_since_close) are set to "--". Cash is part of the total
    # used for % allocation.
    def CalculateHoldingInfo(self, holdings):
        enriched = []
        cashAmount = self.GetCashAmount()   # gets the cash amount we currently have
        total_value = cashAmount

        for holding in holdings:
            num_shares = holding["num_shares"]
            curr_price = holding["curr_price"]
            previous_close = holding["previous_close"]

            # A throttled Yahoo answers with fields missing rather than raising,
            # so a quote can arrive with no previous close, or no price at all.
            # The row keeps whatever it does know and carries "--" for the rest,
            # the same way the cash row does, instead of failing the whole page.
            priced = curr_price is not None
            comparable = priced and bool(previous_close)

            market_value = num_shares * curr_price if priced else 0
            change_since_close = (num_shares * (curr_price - previous_close)
                                  if comparable else "--")
            change_pct_since_close = ((curr_price - previous_close) /
                                      previous_close * 100) if comparable else "--"
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
                "change_pct_since_close": change_pct_since_close,
            })

        # add cash as a holding, with "--" for the fields that don't apply to it.
        # it goes at the front so the table always leads with the cash row.
        enriched.insert(0, {
            "symbol": "--",
            "name": "Cash",
            "h_type": "Cash",
            "num_shares": "--",
            "curr_price": "--",
            "previous_close": "--",
            "market_value": cashAmount,
            "change_since_close": "--",
            "change_pct_since_close": "--",
        })

        # second pass: now that we know the portfolio total (holdings + cash), set each holding's % allocation
        for holding in enriched:
            holding["allocation_pct"] = (
                holding["market_value"] / total_value * 100) if total_value else 0

        return enriched

    # Aggregates market value of holdings by type (cash is included as the "Cash" type,
    # since CalculateHoldingInfo adds it as a holding).
    # Returns a list of {h_type, market_value, allocation_pct}, sorted by type name so a
    # type keeps the same slice colour from one refresh to the next -- sorting by value
    # would repaint the chart whenever two types swapped places.

    def CalculateAllocationByType(self, holdings):
        value_by_type = {}
        total_value = 0

        for holding in holdings:
            h_type = holding["h_type"]
            market_value = holding["market_value"]

            value_by_type[h_type] = value_by_type.get(h_type, 0) + market_value
            total_value += market_value

        allocations = []
        for h_type in sorted(value_by_type):
            value = value_by_type[h_type]
            allocations.append({
                "h_type": h_type,
                "market_value": value,
                "allocation_pct": (value / total_value * 100) if total_value else 0,
            })

        return allocations

    # Measures the portfolio's market risk using beta
    #
    # Yahoo doesn't have a beta for every security. A holding whose beta is unknown
    # is left out of the average rather than counted as 0.0 -- counting it as 0.0
    # would be calling it cash, and would understate risk. What got left
    # out is reported as coverage_pct, so the caller can tell whether the number
    # describes the whole portfolio or only a slice of it.
    #
    # Returns:
    #   {portfolio_beta: 1.05, risk_level: "Market", coverage_pct: 92.4,
    #    total_value: ..., covered_value: ...,
    #    holdings: [{symbol, name, h_type, beta, market_value, weight_pct,
    #                contribution, risk_share_pct}, ...],
    #    unpriced: ["XYZ", ...],
    #    highlight: {symbol, name, weight_pct, risk_share_pct, direction} | None}
    # holdings is sorted by contribution, so the biggest sources of risk lead.

    def CalculatePortfolioRisk(self):
        dbHoldingsRes = self.db_manager.get_holdings()

        quotes = self.finance_manager.get_stocks_by_tickers(
            [holding.ticker for holding in dbHoldingsRes])

        cashAmount = self.GetCashAmount()

        # cash has 0.0 beta
        total_value = cashAmount
        covered_value = cashAmount
        unpriced = []

        rows = [{
            "symbol": "--",
            "name": "Cash",
            "h_type": "Cash",
            "beta": 0.0,
            "market_value": cashAmount,
        }]

        for holding in dbHoldingsRes:
            quote = quotes.get(holding.ticker)

            # skip if there is no beta
            if quote is None or quote["current_price"] is None:
                unpriced.append(holding.ticker)
                continue

            market_value = holding.quantity_shares * quote["current_price"]
            total_value += market_value

            beta = quote["beta"]
            if beta is not None:
                covered_value += market_value

            rows.append({
                "symbol": holding.ticker,
                "name": holding.name,
                "h_type": holding.h_type,
                "beta": beta,
                "market_value": market_value,
            })


        for row in rows:
            if row["beta"] is None or not covered_value:
                row["weight_pct"] = 0
                row["contribution"] = 0
                continue

            weight = row["market_value"] / covered_value
            row["weight_pct"] = weight * 100
            row["contribution"] = weight * row["beta"]

        portfolio_beta = sum(row["contribution"] for row in rows)

        # each holding's share of the portfolio's beta, as a percent
        # An unrated holding lands = 0, like cash does,
        for row in rows:
            row["risk_share_pct"] = (row["contribution"] / portfolio_beta * 100
                                     ) if portfolio_beta else 0

        rows.sort(key=lambda row: row["contribution"], reverse=True)

        return {
            "portfolio_beta": portfolio_beta,
            "risk_level": self.ClassifyRiskLevel(portfolio_beta),
            "coverage_pct": (covered_value / total_value * 100) if total_value else 0,
            "total_value": total_value,
            "covered_value": covered_value,
            "holdings": rows,
            "unpriced": unpriced,
            "highlight": self.FindRiskHighlight(rows),
            # the thresholds risk_level was decided with, so the meter can shade
            # the same bands it labels. Sent rather than repeated in the frontend
            # so tuning the constants above can't leave the two disagreeing.
            "beta_bands": {
                "conservative_ceiling": _CONSERVATIVE_BETA_CEILING,
                "market_ceiling": _MARKET_BETA_CEILING,
            },
        }

    # Picks the holding whose share of the risk is furthest from its share of the
    # money, for information for user
    # Returns the numbers, not the wording, so the copy stays in the component.
    #
    # Cash is skipped (it is 0 beta by definition, so it always diverges and never
    # says anything), and so are unrated holdings (no risk share to compare).
    # Returns None when nothing diverges enough to be worth a claim.

    def FindRiskHighlight(self, rows):
        candidates = [row for row in rows
                      if row["beta"] is not None and row["h_type"] != "Cash"]
        if not candidates:
            return None

        top = max(candidates,
                  key=lambda row: abs(row["risk_share_pct"] - row["weight_pct"]))

        gap = top["risk_share_pct"] - top["weight_pct"]
        if abs(gap) < _RISK_HIGHLIGHT_MIN_GAP_PCT:
            return None

        return {
            "symbol": top["symbol"],
            "name": top["name"],
            "weight_pct": top["weight_pct"],
            "risk_share_pct": top["risk_share_pct"],
            # which way to word it: "but" vs "but only"
            "direction": "above" if gap > 0 else "below",
        }

    # Turns a beta into the plain-language bucket the UI can label it with. The
    # thresholds are a presentation choice, not a financial standard -- they're
    # here so the wording stays consistent wherever risk gets shown.

    def ClassifyRiskLevel(self, beta: float) -> str:
        if beta < _CONSERVATIVE_BETA_CEILING:
            return "Conservative"
        if beta <= _MARKET_BETA_CEILING:
            return "Market"
        return "Aggressive"

    def get_top_movers(self) -> list[dict]:
        return self.finance_manager.get_top_movers()
