import re
import os
from zoneinfo import ZoneInfo
from collections import namedtuple
from db_items import Holding, Transaction
from db_manager import DBManager
from finance_manager import FinanceManager
from typing import List, Optional
from datetime import datetime, timezone
import bisect

_CONSERVATIVE_BETA_CEILING = 0.8
_MARKET_BETA_CEILING = 1.2
# difference threshold between a holding's share of the risk and a holidng's share of the portfolio
_RISK_HIGHLIGHT_MIN_GAP_PCT = 3.0

# --- TEMPORARY: seed-transaction fallback for cost basis -------------------
# A local dev database seeded before db/seed_dummy_data.sql was reconciled
# (or never reseeded since) has holdings rows for the demo tickers with no
# matching transaction rows behind them, so CalculateCostBasis has nothing to
# compute their average cost from. Rather than hand-copy that file's
# transaction rows here (which would silently drift out of sync the next
# time someone edits the seed file), this reads and parses that file
# directly, so it's never a second copy of the data -- just a different view
# of the same one file. Used ONLY for a ticker that has zero real rows in the
# transactions table; a ticker with any real history always uses that
# instead and is never blended with this fallback.
# NOTE: db/ is excluded from the Vercel deployment (see .vercelignore), so
# this file won't exist there -- _load_seed_transactions() returns [] in that
# case, and CalculateCostBasis falls back to nothing beyond real transactions,
# same as if this whole block didn't exist. Local dev only, by design.
# DELETE THIS once every environment has been reseeded with the current
# seed_dummy_data.sql, so cost basis always comes from the real transactions
# table -- this exists purely as a bridge until then, not a design choice.
_SeedTxn = namedtuple(
    "_SeedTxn", ["ticker", "quantity", "price", "trans_date", "action_taken"]
)

_SEED_SQL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "db", "seed_dummy_data.sql"
)
_SEED_ROW_PATTERN = re.compile(
    r"\(\s*'([A-Za-z]+)'\s*,\s*(\d+)\s*,\s*([\d.]+)\s*,\s*'([\d\-: ]+)'\s*,\s*'(buy|sell)'\s*\)"
)


def _load_seed_transactions():
    try:
        with open(_SEED_SQL_PATH, "r") as f:
            sql = f.read()
    except OSError:
        return []

    # isolate just the "INSERT INTO transactions (...) VALUES (...), (...);"
    # block, so this can't accidentally match rows from a different INSERT
    # elsewhere in the file (e.g. holdings or portfolio_value)
    match = re.search(
        r"INSERT INTO transactions\s*\([^)]*\)\s*VALUES\s*(.*?);",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    seed_transactions = []
    for row in _SEED_ROW_PATTERN.finditer(match.group(1)):
        ticker, quantity, price, date_str, action = row.groups()
        seed_transactions.append(
            _SeedTxn(
                ticker=ticker,
                quantity=int(quantity),
                price=float(price),
                trans_date=datetime.strptime(
                    date_str.strip(), "%Y-%m-%d %H:%M:%S"),
                action_taken=action,
            )
        )

    return seed_transactions


# parsed once at import time rather than on every call to CalculateCostBasis
_SEED_TRANSACTIONS = _load_seed_transactions()
# ---------------------------------------------------------------------------


class PortfolioManager:
    """Handles all portfolio-related queries and calculations.

    Delegates database access and market data lookups to DBManager and
    FinanceManager respectively.
    """

    def __init__(self, db_manager: DBManager, finance_manager: FinanceManager):
        """Inits PortfolioManager with required data managers.

        Args:
            db_manager: Instance handling database queries and updates.
            finance_manager: Instance handling financial quote lookups.
        """
        self.db_manager = db_manager
        self.finance_manager = finance_manager

    def _get_holdings_with_price(self) -> list[dict]:
        """Fetches database holdings and enriches them with batch market quotes.

        Returns:
            list[dict]: A list of holdings containing price and sector details.

        Raises:
            ValueError: If a holding ticker cannot be found or validated.
        """
        db_holding_res = self.db_manager.get_holdings()

        quotes = self.finance_manager.get_stocks_by_tickers(
            [holding.ticker for holding in db_holding_res]
        )

        holdings_with_price = []
        for holding in db_holding_res:
            yahoo_res = quotes.get(holding.ticker)
            if yahoo_res is None:
                raise ValueError("Holding must be a valid security.")
            holdings_with_price.append(
                {
                    "symbol": holding.ticker,
                    "name": holding.name,
                    "h_type": holding.h_type,
                    "num_shares": holding.quantity_shares,
                    "curr_price": yahoo_res["current_price"],
                    "previous_close": yahoo_res["previous_close"],
                    "sector": yahoo_res.get("sector") or "Other",
                }
            )

        return holdings_with_price

    def empty_caches(self) -> None:
        """Flushes memory caches across finance and database managers."""
        self.finance_manager.empty_cache()
        self.db_manager.empty_cache()

    def get_overview_data(self) -> dict:
        """Retrieves and packages all data required for the Overview dashboard.

        Returns:
            dict: Comprehensive dataset containing:
                - HoldingsTable: List of enriched holdings.
                - Allocations: Asset breakdown by category.
                - AllocationsBySector: Asset breakdown by industry sector.
                - PortfolioSummary: Total value and daily movement metrics.
                - PortfolioHistory: Value history snapshots.
                - TopMovers: Watchlist market movers.
                - LastUpdated: ISO timestamp of when the quotes were pulled.
        """
        final_res = {}

        holdings_with_price = self._get_holdings_with_price()
        enriched_holdings = self.calculate_holding_info(holdings_with_price)
        final_res["HoldingsTable"] = enriched_holdings

        allocations = self.calculate_allocation_by_field(
            enriched_holdings, "h_type")
        final_res["Allocations"] = allocations
        final_res["AllocationsBySector"] = self.calculate_allocation_by_field(
            enriched_holdings, "sector"
        )

        summary = self.db_manager.get_portfolio_values()[0].to_dict()
        final_res["PortfolioSummary"] = summary

        final_res["PortfolioHistory"] = self.get_portfolio_history(
            todays_value=summary["total_value"]
        )

        final_res["TopMovers"] = self._get_top_movers()

        final_res["LastUpdated"] = datetime.now().astimezone().isoformat()

        return final_res

    def _get_enriched_holdings(self) -> list[dict]:
        """Fetches current holdings and builds enriched details including cash.

        Returns:
            list[dict]: Enriched holdings calculated with current price quotes.
        """
        holdings_with_price = self._get_holdings_with_price()
        return self.calculate_holding_info(holdings_with_price)

    def get_biggest_gainer_and_loser(self) -> dict:
        """Determines the top performing and worst performing holdings by unrealized gain.

        Evaluates active non-cash positions against their computed average cost basis
        to find the highest and lowest percentage returns since purchase. Holdings
        lacking a computable cost basis or valid price are excluded and tracked
        separately.

        Returns:
            dict: A dictionary containing performance analytics with the following keys:
                - "biggest_gainer" (dict | None): The holding with the highest percentage gain.
                - "biggest_loser" (dict | None): The holding with the lowest percentage gain.
                - "qualifying_count" (int): Number of positions with a valid cost basis.
                - "total_positions" (int): Total count of non-cash holdings evaluated.
                - "excluded_symbols" (list[str]): Symbols excluded due to missing cost basis or price.
        """
        enriched_holdings = self._get_enriched_holdings()
        cost_basis_by_ticker = self.calculate_cost_basis()

        movers = []
        excluded_symbols = []
        total_positions = 0

        for holding in enriched_holdings:
            ticker = holding["symbol"]
            if ticker == "--":  # the cash row -- not a position, don't count or list it
                continue
            total_positions += 1

            curr_price = holding["curr_price"]
            avg_cost = cost_basis_by_ticker.get(ticker)

            if avg_cost is None or not isinstance(curr_price, (int, float)):
                excluded_symbols.append(ticker)
                continue

            gain_pct = (curr_price - avg_cost) / \
                avg_cost * 100 if avg_cost else 0
            movers.append(
                {
                    "symbol": ticker,
                    "name": holding["name"],
                    "curr_price": curr_price,
                    "avg_cost_basis": avg_cost,
                    "gain_since_purchase": (curr_price - avg_cost)
                    * holding["num_shares"],
                    "gain_pct_since_purchase": gain_pct,
                }
            )

        if not movers:
            return {
                "biggest_gainer": None,
                "biggest_loser": None,
                "qualifying_count": 0,
                "total_positions": total_positions,
                "excluded_symbols": excluded_symbols,
            }

        biggest_gainer = max(
            movers, key=lambda holding: holding["gain_pct_since_purchase"]
        )
        biggest_loser = min(
            movers, key=lambda holding: holding["gain_pct_since_purchase"]
        )

        return {
            "biggest_gainer": biggest_gainer,
            "biggest_loser": biggest_loser,
            "qualifying_count": len(movers),
            "total_positions": total_positions,
            "excluded_symbols": excluded_symbols,
        }

    def _get_top_movers(self, count: int = 5) -> list[dict]:
        """Fetches top market movers for the user's watchlist.

        Args:
            count: Number of movers to retrieve. Defaults to 5.

        Returns:
            list[dict]: Reshaped market quotes containing symbol, name, price,
            and percent change. Skips invalid or unpriceable quotes.
        """
        final_res = []

        for mover in self.finance_manager.get_top_movers(count):
            price = mover["curr_price"]
            previous_close = mover["previous_close"]

            if price is None or not previous_close:
                continue

            final_res.append(
                {
                    "symbol": mover["symbol"],
                    "name": mover["name"],
                    "price": price,
                    "change": (price - previous_close) / previous_close * 100,
                }
            )

        return final_res

    def calculate_cost_basis(self) -> dict[str, float]:
        """Calculates the average cost basis per share for currently held securities.

        Replays the full buy/sell transaction history in chronological order using
        the average-cost method. If real transaction data is missing for a ticker,
        it falls back to seed transaction records. Closed positions (net zero or
        negative remaining shares) are omitted from the output.

        Returns:
            dict[str, float]: A mapping of ticker symbols to their calculated
                average cost basis per share.
        """
        transactions = self.db_manager.get_transactions()

        by_ticker = {}
        for t in transactions:
            by_ticker.setdefault(t.ticker, []).append(t)

        # frozen *before* the fallback is added, so a multi-row seed ticker
        # (e.g. NVDA has three rows) doesn't get cut short after its first
        # fallback row makes it look like it "has data" to the checks below
        tickers_with_real_data = set(by_ticker)

        for seed_txn in _SEED_TRANSACTIONS:
            if seed_txn.ticker not in tickers_with_real_data:
                by_ticker.setdefault(seed_txn.ticker, []).append(seed_txn)

        cost_basis = {}
        for ticker, txns in by_ticker.items():
            txns.sort(key=lambda t: t.trans_date)
            running_shares = 0
            running_cost = 0.0

            for t in txns:
                # price is a Decimal (comes from a Postgres DECIMAL column)
                # for a real row, or a plain float for a fallback row; cast
                # either way so it doesn't collide with running_cost's type
                price = float(t.price)

                if t.action_taken == "buy":
                    running_shares += t.quantity
                    running_cost += t.quantity * price
                elif t.action_taken == "sell" and running_shares > 0:
                    avg_cost = running_cost / running_shares
                    sold = min(t.quantity, running_shares)
                    running_cost -= avg_cost * sold
                    running_shares -= sold

            if running_shares > 0:
                cost_basis[ticker] = running_cost / running_shares

        return cost_basis

    def get_portfolio_history(
        self,
        todays_value: Optional[float] = None,
        benchmark_ticker: str = "^GSPC",
    ) -> list[dict]:
        """Retrieves historical portfolio snapshots alongside benchmark index values.

        Normalizes raw historical data chronologically and appends or updates
        today's live portfolio value if provided. Matches benchmark closing levels
        to each snapshot date.

        Args:
            todays_value: Current live portfolio value.
            benchmark_ticker: Benchmark ticker to compare against. Defaults to "^GSPC".

        Returns:
            list[dict]: Chronological list of snapshots formatted as:
                [{"date": str, "value": float, "benchmark_value": float | None}]
        """
        db_res = self.db_manager.get_portfolio_values()

        history = []
        for pv in sorted(db_res, key=lambda pv: pv.p_date):
            dt_str = pv.p_date.isoformat()
            history.append(
                {
                    "date": dt_str,
                    "value": float(pv.value),
                }
            )

        if todays_value is not None:
            today_dt = datetime.now(timezone.utc).isoformat()
            if history and history[-1]["date"][:10] == today_dt[:10]:
                history[-1]["value"] = todays_value
                history[-1]["date"] = today_dt
            else:
                history.append({"date": today_dt, "value": todays_value})

        benchmark_closes = self.finance_manager.get_index_history(
            benchmark_ticker)
        if benchmark_closes:
            benchmark_dates = sorted(benchmark_closes)

            def _closest_close(iso_date_str):
                ymd = iso_date_str[:10]
                i = bisect.bisect_right(benchmark_dates, ymd)
                return benchmark_closes[benchmark_dates[i - 1]] if i > 0 else None

            for point in history:
                point["benchmark_value"] = _closest_close(point["date"])
        else:
            for point in history:
                point["benchmark_value"] = None

        return history

    def get_drawdown_and_runup(self) -> dict:
        """Calculates the maximum drawdown and run-up metrics across historical values.

        Evaluates historical data including the live total value to track peak-to-trough
        declines and trough-to-peak gains.

        Returns:
            dict: Structured drawdown and run-up details:
                {
                    "drawdown": dict | None,
                    "runup": dict | None
                }
        """
        enrichedHoldings = self._get_enriched_holdings()
        summary = self.calculate_portfolio_summary(enrichedHoldings)
        history = self.get_portfolio_history(
            todays_value=summary["total_value"])

        if len(history) < 2:
            return {"drawdown": None, "runup": None}

        def _parse(date_str):
            return datetime.fromisoformat(date_str).date()

        def _day(date_str):
            return _parse(date_str).isoformat() if date_str else None

        peak_value, peak_date = (
            history[0]["value"],
            history[0]["date"],
        )
        max_dd_pct = 0
        dd_peak_value = dd_peak_date = dd_trough_value = dd_trough_date = None

        for point in history:
            if point["value"] > peak_value:
                peak_value, peak_date = point["value"], point["date"]
            else:
                pct = (
                    (point["value"] - peak_value) / peak_value * 100
                    if peak_value
                    else 0
                )
                if pct < max_dd_pct:
                    max_dd_pct = pct
                    dd_peak_value, dd_peak_date = (
                        peak_value,
                        peak_date,
                    )
                    dd_trough_value, dd_trough_date = (
                        point["value"],
                        point["date"],
                    )

        drawdown = None
        if dd_trough_date is not None:
            recovered_date = next(
                (
                    point["date"]
                    for point in history
                    if point["date"] > dd_trough_date
                    and point["value"] >= dd_peak_value
                ),
                None,
            )
            recovery_days = (
                (_parse(recovered_date) - _parse(dd_trough_date)).days
                if recovered_date
                else None
            )

            drawdown = {
                "pct": max_dd_pct,
                "peak_value": dd_peak_value,
                "peak_date": _day(dd_peak_date),
                "trough_value": dd_trough_value,
                "trough_date": _day(dd_trough_date),
                "decline_days": (_parse(dd_trough_date) - _parse(dd_peak_date)).days,
                "recovered_date": _day(recovered_date),
                "recovery_days": recovery_days,
            }

        trough_value, trough_date = (
            history[0]["value"],
            history[0]["date"],
        )
        max_ru_pct = 0
        ru_trough_value = ru_trough_date = ru_peak_value = ru_peak_date = None

        for point in history:
            if point["value"] < trough_value:
                trough_value, trough_date = (
                    point["value"],
                    point["date"],
                )
            else:
                pct = (
                    (point["value"] - trough_value) / trough_value * 100
                    if trough_value
                    else 0
                )
                if pct > max_ru_pct:
                    max_ru_pct = pct
                    ru_trough_value, ru_trough_date = (
                        trough_value,
                        trough_date,
                    )
                    ru_peak_value, ru_peak_date = (
                        point["value"],
                        point["date"],
                    )

        runup = None
        if ru_peak_date is not None:
            latest_value = history[-1]["value"]
            since_peak_pct = (
                (latest_value - ru_peak_value) / ru_peak_value * 100
                if ru_peak_value
                else 0
            )

            runup = {
                "pct": max_ru_pct,
                "trough_value": ru_trough_value,
                "trough_date": _day(ru_trough_date),
                "peak_value": ru_peak_value,
                "peak_date": _day(ru_peak_date),
                "incline_days": (_parse(ru_peak_date) - _parse(ru_trough_date)).days,
                "since_peak_pct": since_peak_pct,
                "at_new_high": since_peak_pct >= 0,
            }

        return {"drawdown": drawdown, "runup": runup}

    def calculate_portfolio_summary(self, holdings: List[dict]) -> dict:
        """Calculates current total value and day change metrics across holdings.

        Args:
            holdings: List of enriched holding records.

        Returns:
            dict: Summary metrics containing:
                - total_value: Total portfolio market value including cash.
                - day_change: Dollar movement since previous close.
                - day_change_pct: Percentage movement since previous close.
        """
        total_value = sum(holding["market_value"] for holding in holdings)

        day_change = sum(
            holding["change_since_close"]
            for holding in holdings
            if isinstance(holding["change_since_close"], (int, float))
        )

        previous_value = total_value - day_change
        day_change_pct = (day_change / previous_value *
                          100) if previous_value else 0

        return {
            "total_value": total_value,
            "day_change": day_change,
            "day_change_pct": day_change_pct,
        }

    def get_transactions(self) -> list[dict]:
        """Retrieves transaction history ledger from the database.

        Returns:
            list[dict]: Historical record list with transaction details.
        """
        final_res = []
        dbTransRes = self.db_manager.get_transactions()
        for trans in dbTransRes:
            final_res.append(
                {
                    "date": trans.trans_date,
                    "ticker": trans.ticker,
                    "quantity": trans.quantity,
                    "price": trans.price,
                    "action": trans.action_taken,
                }
            )
        return final_res

    def buy(self, ticker: str, quantity: int) -> None:
        """Executes a buy order for a security.

        Deducts the total purchase cost from cash, creates or updates the holding,
        and logs the action in the transaction history.

        Args:
            ticker: Security ticker symbol.
            quantity: Number of shares to purchase. Must be positive.
            price: Cost per share.

        Raises:
            ValueError: If quantity is non-positive, cash is insufficient, or security is invalid.
        """
        if quantity <= 0:
            raise ValueError("quantity must be a positive number of shares")

        yahoo_data = self.finance_manager.get_stock_by_ticker(ticker)
        if yahoo_data is None:
            raise ValueError("Holding must be a valid security.")

        price = yahoo_data["current_price"]

        total_cost = quantity * price
        cash = self.get_cash_amount()
        if total_cost > cash:
            raise ValueError("insufficient cash to complete this purchase")

        existing = self.db_manager.get_holding(ticker)
        if existing is None:
            self.db_manager.add_holding(
                Holding(
                    ticker,
                    yahoo_data["name"],
                    yahoo_data["stock_type"],
                    quantity,
                )
            )
        else:
            existing.quantity_shares += quantity
            self.db_manager.update_holding(existing)

        self.db_manager.set_cash((cash - total_cost))

        self.db_manager.add_transaction(
            Transaction(None, ticker, quantity, price, datetime.now(), "buy")
        )

    def sell(self, ticker: str, quantity: int) -> None:
        """Executes a sell order for a security position.

        Adds sale proceeds to cash, decreases or removes the holding, and logs
        the action in the transaction history.

        Args:
            ticker: Security ticker symbol.
            quantity: Number of shares to sell. Must be positive.
            price: Sale price per share.

        Raises:
            ValueError: If quantity is non-positive or exceeds currently held shares.
        """
        if quantity <= 0:
            raise ValueError("quantity must be a positive number of shares")

        yahoo_data = self.finance_manager.get_stock_by_ticker(ticker)
        if yahoo_data is None:
            raise ValueError("Holding must be a valid security.")

        existing = self.db_manager.get_holding(ticker)
        if existing is None or existing.quantity_shares < quantity:
            raise ValueError("cannot sell more shares than are currently held")

        cash = self.get_cash_amount()

        price = yahoo_data["current_price"]
        sellAmount = quantity * price

        self.db_manager.set_cash((cash + sellAmount))

        existing.quantity_shares -= quantity
        if existing.quantity_shares == 0:
            self.db_manager.delete_holding(existing)
        else:
            self.db_manager.update_holding(existing)

        self.db_manager.add_transaction(
            Transaction(None, ticker, quantity, price, datetime.now(), "sell")
        )

    def get_cash_amount(self) -> float:
        """Retrieves the current cash balance.

        Returns:
            float: Total cash amount, defaulting to 0 if none recorded.
        """
        db_res = self.db_manager.get_cash()
        if db_res:
            return db_res
        else:
            return 0

    def calculate_holding_info(self, holdings: list[dict]) -> list[dict]:
        """Enriches raw holdings data with current value, daily movement, and allocation.

        Appends cash as an explicit leading entry.

        Args:
            holdings: List of dicts representing raw security positions with market quotes.

        Returns:
            list[dict]: Enriched holdings list leading with Cash, including market values,
            daily dollar/percent changes, and portfolio allocation percentages.
        """
        enriched = []
        cash_amount = self.get_cash_amount()
        total_value = cash_amount

        for holding in holdings:
            num_shares = holding["num_shares"]
            curr_price = holding["curr_price"]
            previous_close = holding["previous_close"]

            priced = curr_price is not None
            comparable = priced and bool(previous_close)

            market_value = num_shares * curr_price if priced else 0
            change_since_close = (
                (num_shares * (curr_price - previous_close)) if comparable else "--"
            )
            change_pct_since_close = (
                ((curr_price - previous_close) / previous_close * 100)
                if comparable
                else "--"
            )
            total_value += market_value

            enriched.append(
                {
                    "symbol": holding["symbol"],
                    "name": holding["name"],
                    "h_type": holding["h_type"],
                    "sector": holding.get("sector", "Other"),
                    "num_shares": num_shares,
                    "curr_price": curr_price,
                    "previous_close": previous_close,
                    "market_value": market_value,
                    "change_since_close": change_since_close,
                    "change_pct_since_close": change_pct_since_close,
                }
            )

        enriched.insert(
            0,
            {
                "symbol": "--",
                "name": "Cash",
                "h_type": "Cash",
                "sector": "Cash",
                "num_shares": "--",
                "curr_price": "--",
                "previous_close": "--",
                "market_value": cash_amount,
                "change_since_close": "--",
                "change_pct_since_close": "--",
            },
        )

        for holding in enriched:
            holding["allocation_pct"] = (
                (holding["market_value"] /
                 total_value * 100) if total_value else 0
            )

        return enriched

    def calculate_allocation_by_field(
        self, holdings: List[dict], field: str
    ) -> list[dict]:
        """Aggregates portfolio market value and allocation grouped by a specific field.

        Args:
            holdings: List of enriched holding records.
            field: Dictionary key to aggregate by (e.g., "h_type" or "sector").

        Returns:
            list[dict]: List sorted by label containing label, aggregated market_value,
            and total allocation_pct.
        """
        value_by_label = {}
        total_value = 0

        for holding in holdings:
            label = holding.get(field) or "Other"
            market_value = holding["market_value"]

            value_by_label[label] = value_by_label.get(label, 0) + market_value
            total_value += market_value

        allocations = []
        for label in sorted(value_by_label):
            value = value_by_label[label]
            allocations.append(
                {
                    "label": label,
                    "market_value": value,
                    "allocation_pct": (
                        (value / total_value * 100) if total_value else 0
                    ),
                }
            )

        return allocations

    def calculate_portfolio_risk(self) -> dict:
        """Measures overall portfolio market risk using weighted security betas.

        Computes portfolio beta, risk level categorization, coverage percent,
        and per-holding risk contributions sorted from highest risk contributor.

        Returns:
            dict: Portfolio risk report containing portfolio_beta, risk_level,
            coverage_pct, holdings, unpriced tickers, risk highlights, and beta bands.
        """
        db_holding_res = self.db_manager.get_holdings()

        quotes = self.finance_manager.get_stocks_by_tickers(
            [holding.ticker for holding in db_holding_res]
        )

        cash_amount = self.get_cash_amount()

        total_value = cash_amount
        covered_value = cash_amount
        unpriced = []

        rows = [
            {
                "symbol": "--",
                "name": "Cash",
                "h_type": "Cash",
                "beta": 0.0,
                "market_value": cash_amount,
            }
        ]

        for holding in db_holding_res:
            quote = quotes.get(holding.ticker)

            if quote is None or quote["current_price"] is None:
                unpriced.append(holding.ticker)
                continue

            market_value = holding.quantity_shares * quote["current_price"]
            total_value += market_value

            beta = quote["beta"]
            if beta is not None:
                covered_value += market_value

            rows.append(
                {
                    "symbol": holding.ticker,
                    "name": holding.name,
                    "h_type": holding.h_type,
                    "beta": beta,
                    "market_value": market_value,
                }
            )

        for row in rows:
            if row["beta"] is None or not covered_value:
                row["weight_pct"] = 0
                row["contribution"] = 0
                continue

            weight = row["market_value"] / covered_value
            row["weight_pct"] = weight * 100
            row["contribution"] = weight * row["beta"]

        portfolio_beta = sum(row["contribution"] for row in rows)

        for row in rows:
            row["risk_share_pct"] = (
                (row["contribution"] / portfolio_beta *
                 100) if portfolio_beta else 0
            )

        rows.sort(key=lambda row: row["contribution"], reverse=True)

        return {
            "portfolio_beta": portfolio_beta,
            "risk_level": self.classify_risk_level(portfolio_beta),
            "coverage_pct": ((covered_value / total_value * 100) if total_value else 0),
            "total_value": total_value,
            "covered_value": covered_value,
            "holdings": rows,
            "unpriced": unpriced,
            "highlight": self.find_risk_highlight(rows),
            "beta_bands": {
                "conservative_ceiling": _CONSERVATIVE_BETA_CEILING,
                "market_ceiling": _MARKET_BETA_CEILING,
            },
        }

    def find_risk_highlight(self, rows: list[dict]) -> Optional[dict]:
        """Identifies the holding with the largest divergence between risk share and capital weight.

        Args:
            rows: List of holding dicts calculated during risk analysis.

        Returns:
            dict | None: Highlight summary for the most divergent holding, or None
            if no holding exceeds the minimum divergence gap threshold.
        """
        candidates = [
            row for row in rows if row["beta"] is not None and row["h_type"] != "Cash"
        ]
        if not candidates:
            return None

        top = max(
            candidates,
            key=lambda row: abs(row["risk_share_pct"] - row["weight_pct"]),
        )

        gap = top["risk_share_pct"] - top["weight_pct"]
        if abs(gap) < _RISK_HIGHLIGHT_MIN_GAP_PCT:
            return None

        return {
            "symbol": top["symbol"],
            "name": top["name"],
            "weight_pct": top["weight_pct"],
            "risk_share_pct": top["risk_share_pct"],
            "direction": "above" if gap > 0 else "below",
        }

    def search_securities(self, query: str) -> list[dict]:
        """Searches for securities matching a text query string.

        Args:
            query: Search string for ticker symbol or company name.

        Returns:
            list[dict]: List of matching security records.
        """
        return self.finance_manager.search_securities(query)

    def classify_risk_level(self, beta: float) -> str:
        """Classifies a numerical beta into a human-readable risk category.

        Args:
            beta: Calculated portfolio beta value.

        Returns:
            str: Risk classification ("Conservative", "Market", or "Aggressive").
        """
        if beta < _CONSERVATIVE_BETA_CEILING:
            return "Conservative"
        if beta <= _MARKET_BETA_CEILING:
            return "Market"
        return "Aggressive"

    def get_top_movers(self) -> list[dict]:
        """Fetches general top market movers from the finance manager.

        Returns:
            list[dict]: Raw top mover market quotes.
        """
        return self.finance_manager.get_top_movers()

    def get_news(self) -> list[dict]:
        """Retrieves financial news articles.

        Returns:
            list[dict]: Recent financial news items.
        """
        return self.finance_manager.get_news()

    def update_portfolio_value(self) -> dict:
        """Calculates current portfolio value and logs a new snapshot to the database.

        Returns:
            dict: Summary metrics for the logged snapshot containing total value,
            day change, and day change percentage.
        """
        holdings_with_price = self._get_holdings_with_price()
        enriched_holdings = self.calculate_holding_info(holdings_with_price)

        summary = self.calculate_portfolio_summary(enriched_holdings)
        ny_tz = ZoneInfo("America/New_York")
        portfolio_value: float = summary["total_value"]

        self.db_manager.add_portfolio_value(
            datetime.now(ny_tz),
            portfolio_value,
            summary["day_change"],
            summary["day_change_pct"],
        )
        return summary
