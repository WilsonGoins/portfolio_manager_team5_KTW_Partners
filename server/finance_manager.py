import yfinance as yf
import logging
from concurrent.futures import ThreadPoolExecutor

# Yahoo answers one ticker per request, so the only way to speed up a batch is to
# have several in flight at once. Capped so a large portfolio doesn't open a
# connection per holding and get us rate limited.
_MAX_QUOTE_WORKERS = 8


class FinanceManager:
    """This class is responsible for handling all yahoo finance queries"""

    def __init__(self, flask_logger: logging.Logger):
        self.logger = flask_logger

    def get_stock_by_ticker(self, ticker: str) -> dict:
        """
        Method 1: Query for stock by ticker.
        Returns: current price, stock name, stock type, previous close
        """
        try:
            info = yf.Ticker(ticker).info
            return {
                "ticker": ticker.upper(),
                "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "name": info.get("longName") or info.get("shortName"),
                "stock_type": info.get("quoteType"),
                "previous_close": info.get("previousClose"),
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch stock by ticker '{ticker}': {e}", exc_info=True)
            return None

    def get_stocks_by_tickers(self, tickers: list[str]) -> dict:
        """
        Method 1b: Query for several stocks at once.
        Same per-stock result as get_stock_by_ticker, but the requests are run
        concurrently instead of back to back, so the wait is roughly one round
        trip rather than one per ticker.
        Returns: {ticker: stock dict}, keyed by the ticker as it was passed in.
                 A ticker that couldn't be fetched maps to None, exactly as
                 get_stock_by_ticker would return for it on its own.
        """
        if not tickers:
            return {}

        # dict comprehension dedupes, so a ticker listed twice is only fetched once
        unique_tickers = list(dict.fromkeys(tickers))
        if len(unique_tickers) == 1:
            ticker = unique_tickers[0]
            return {ticker: self.get_stock_by_ticker(ticker)}

        results = {}
        with ThreadPoolExecutor(
                max_workers=min(len(unique_tickers), _MAX_QUOTE_WORKERS)) as executor:
            futures = {ticker: executor.submit(self.get_stock_by_ticker, ticker)
                       for ticker in unique_tickers}

            for ticker, future in futures.items():
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    # get_stock_by_ticker swallows its own failures, so this is
                    # something unexpected -- keep the other tickers' results
                    self.logger.error(
                        f"Failed to fetch stock by ticker '{ticker}': {e}", exc_info=True)
                    results[ticker] = None

        return results

    def get_stock_by_name(self, name: str) -> dict:
        """
        Method 2: Query for stock by name.
        Returns: current price, ticker, stock type, previous close
        """
        try:
            results = yf.Search(name, max_results=1).quotes
            if not results:
                self.logger.warning(f"No search results found for name '{name}'")
                return None

            ticker = results[0]["symbol"]
            stock_data = self.get_stock_by_ticker(ticker)
            if stock_data is None:
                return None

            return {
                "ticker": stock_data["ticker"],
                "current_price": stock_data["current_price"],
                "stock_type": stock_data["stock_type"],
                "previous_close": stock_data["previous_close"],
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch stock by name '{name}': {e}", exc_info=True)
            return None

    def get_top_movers(self, count: int = 5) -> list[dict]:
        """
        Method 3: Query for the 5 biggest movers.
        Returns: ticker, name, current price, previous close, market cap
        """
        try:
            results = yf.screen("day_gainers", count=count)
            quotes = results.get("quotes", [])

            movers = []
            for q in quotes:
                movers.append({
                    "ticker": q.get("symbol"),
                    "name": q.get("longName") or q.get("shortName"),
                    "current_price": q.get("regularMarketPrice"),
                    "previous_close": q.get("regularMarketPreviousClose"),
                    "market_cap": q.get("marketCap"),
                })
            return movers
        except Exception as e:
            self.logger.error(f"Failed to fetch top movers: {e}", exc_info=True)
            return []
    # SHOULD INCLUDE ANY METHODS WE WOULD NEED TO POPULATE EXPLORE PAGE
    # - search functionality to return a specific security from name or symbol
    # - a method to return a FEATURED* list of securities to look at on explore landing poge
    # - other stuff that could be useful??
    #
    # Maybe it would make the codebase neater if instead of returning dicts or wtv it is that
    # yfinance returns we make our own custom security object resembling db_items.Holding for example
