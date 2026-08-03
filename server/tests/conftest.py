"""Test setup.

These are integration tests: they send real HTTP requests to the real Flask
app, which runs the real PortfolioManager. Only the two things a test can't
reach are faked -- the Postgres database and Yahoo Finance -- so everything
between the URL and those two edges is the actual application code.

The fake portfolio every test starts from:

    cash                        $5,000
    AAPL   10 shares @ $200     $2,000   (yesterday's close $190)
    SPY    20 shares @ $500    $10,000   (yesterday's close $500)
    ------------------------------------
    total                      $17,000   of which $100 is today's move
"""

import os
import sys
from datetime import date, datetime

import pytest

from db_items import Holding, PortfolioValue, Transaction
from portfolio_manager import PortfolioManager


# --------------------------------------------------------------------------
# the two fakes
# --------------------------------------------------------------------------

class FakeDB:
    """An in-memory stand-in for DBManager, holding the portfolio above."""

    def __init__(self):
        self.cash = 5000.0
        self.holdings = [
            Holding("AAPL", "Apple Inc.", "EQUITY", 10),
            Holding("SPY", "SPDR S&P 500 ETF", "ETF", 20),
        ]
        self.transactions = [
            Transaction(1, "AAPL", 10, 150.0, datetime(2026, 4, 28, 10, 0),
                        "buy"),
            Transaction(2, "SPY", 20, 480.0, datetime(2026, 5, 12, 10, 0),
                        "buy"),
        ]
        # newest first, the way the real query orders them
        self.portfolio_values = [
            PortfolioValue(date(2026, 7, 15), 12000.0, -300.0, -2.44),
            PortfolioValue(date(2026, 7, 1), 15000.0, 100.0, 0.67),
        ]

    def get_cash(self):
        return self.cash

    def set_cash(self, new_value):
        self.cash = new_value
        return new_value

    def get_holdings(self):
        return list(self.holdings)

    def get_holding(self, ticker):
        for holding in self.holdings:
            if holding.ticker == ticker:
                return holding
        return None

    def add_holding(self, holding):
        self.holdings.append(holding)
        return list(self.holdings)

    def update_holding(self, holding):
        return list(self.holdings)

    def delete_holding(self, holding):
        self.holdings = [h for h in self.holdings if h.ticker != holding.ticker]
        return list(self.holdings)

    def get_transactions(self):
        return list(self.transactions)

    def add_transaction(self, transaction):
        self.transactions.append(transaction)
        return list(self.transactions)

    def get_portfolio_values(self):
        return list(self.portfolio_values)

    def add_portfolio_value(self, p_date, value, change, change_pct):
        self.portfolio_values.insert(
            0, PortfolioValue(p_date, value, change, change_pct))
        return list(self.portfolio_values)


class FakeFinance:
    """Canned Yahoo answers, in the shape the real FinanceManager returns."""

    QUOTES = {
        "AAPL": {"ticker": "AAPL", "name": "Apple Inc.", "stock_type": "EQUITY",
                 "current_price": 200.0, "previous_close": 190.0,
                 "sector": "Technology", "beta": 1.2},
        "SPY": {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "stock_type": "ETF",
                "current_price": 500.0, "previous_close": 500.0,
                "sector": "Large Blend", "beta": 1.0},
        # not held, so it's the one a Buy test can open a new position in
        "NVDA": {"ticker": "NVDA", "name": "NVIDIA Corp", "stock_type": "EQUITY",
                 "current_price": 100.0, "previous_close": 100.0,
                 "sector": "Technology", "beta": 1.8},
    }

    def __init__(self):
        self.cache_emptied = 0

    def get_stock_by_ticker(self, ticker):
        return self.QUOTES.get(ticker)

    def get_stocks_by_tickers(self, tickers):
        return {ticker: self.QUOTES.get(ticker) for ticker in tickers}

    def get_top_movers(self, count=5):
        return [{"symbol": "GME", "name": "GameStop", "curr_price": 55.0,
                 "previous_close": 50.0}]

    def get_index_history(self, ticker="^GSPC"):
        return {"2026-07-01": 4700.0, "2026-07-15": 4650.0}

    def get_news(self, limit=5):
        return [{"title": "Markets rally", "publisher": "Reuters",
                 "url": "https://news.example/1", "image_url": None,
                 "ticker": "SPY"}]

    def search_securities(self, query, max_results=5):
        return [{"symbol": "AAPL", "name": "Apple Inc.", "curr_price": 200.0}]

    def empty_cache(self):
        self.cache_emptied += 1


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """The real Flask app, imported with nothing pointed at a real database.

    api.py opens a connection pool at import time, so the pool is replaced
    before the import happens.
    """
    import db_manager

    # load_dotenv() doesn't override what's already set, so these win over a
    # developer's real .env: no live database, and no background thread.
    os.environ["DB_CONNECTION_STRING"] = "postgresql://test/test"
    os.environ["UPDATE_PORTFOLIO_VALUE"] = ""

    class StubPool:
        check_connection = staticmethod(lambda conn: None)

        def __init__(self, *args, **kwargs):
            pass

        def open(self, *args, **kwargs):
            pass

    real_pool = db_manager.ConnectionPool
    db_manager.ConnectionPool = StubPool
    sys.modules.pop("api", None)
    try:
        import api
    finally:
        db_manager.ConnectionPool = real_pool

    return api


@pytest.fixture
def db():
    return FakeDB()


@pytest.fixture
def finance():
    return FakeFinance()


@pytest.fixture
def client(app, db, finance):
    """A test client for the app, wired to a fresh fake portfolio."""
    app.db_manager = db
    app.finance_manager = finance
    app.portfolio_manager = PortfolioManager(db, finance)
    app._last_refresh_at = None    # reset the refresh throttle between tests

    return app.app.test_client()
