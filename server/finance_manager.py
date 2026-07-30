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
        Method 2: Query for stocks by name/ticker (fuzzy).
        Returns up to `max_results` closely matching securities, ranked by relevance.
        Each result: current price, ticker, name, stock type, previous close.
        """
        query = name.strip()
        if not query:
            self.logger.warning("Empty search query received")
            return []

        try:
            results = yf.Search(query, max_results=max_results).quotes
            if not results:
                self.logger.warning(f"No search results found for '{query}'")
                return []

            matches = []
            for r in results:
                ticker = r.get("symbol")
                stock_data = self.get_stock_by_ticker(ticker)
                if stock_data is not None:
                    matches.append(stock_data)
            return matches
        except Exception as e:
            self.logger.error(f"Failed to fetch stocks by name '{query}': {e}", exc_info=True)
            return []

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

    def search_securities(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Searches for securities matching a name/ticker query and returns
        richly-detailed data for each, matching what the Explore page's
        SecurityCard component needs (price, ratios, 52wk range, chart history).
        """
        query = query.strip()
        if not query:
            self.logger.warning("Empty securities search query received")
            return []

        try:
            results = yf.Search(query, max_results=max_results).quotes
            securities = []
            for r in results:
                enriched = self._get_security_details(r.get("symbol"))
                if enriched is not None:
                    securities.append(enriched)
            return securities
        except Exception as e:
            self.logger.error(f"Failed to search securities for '{query}': {e}", exc_info=True)
            return []

    def _get_security_details(self, ticker: str) -> dict:
        """Builds the full SecurityCard-shaped dict for a single ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            previous_close = info.get("previousClose")

            return {
                "symbol": ticker.upper(),
                "name": info.get("longName") or info.get("shortName"),
                "h_type": info.get("quoteType"),
                "curr_price": current_price,
                "previous_close": previous_close,
                "change_since_close": (current_price or 0) - (previous_close or 0),
                "pe_ratio": info.get("trailingPE"),
                "market_cap": info.get("marketCap"),
                "high_52wk": info.get("fiftyTwoWeekHigh"),
                "low_52wk": info.get("fiftyTwoWeekLow"),
                "volume": info.get("volume"),
                "performanceHistory": self._get_performance_history(stock),
            }
        except Exception as e:
            self.logger.error(f"Failed to get details for '{ticker}': {e}", exc_info=True)
            return None

    def _get_performance_history(self, stock: "yf.Ticker") -> dict:
        """Builds the 1W/1M/1Y/YTD chart data SecurityCard expects."""
        ranges = {"1W": "5d", "1M": "1mo", "1Y": "1y", "YTD": "ytd"}
        history = {}
        for label, period in ranges.items():
            try:
                hist = stock.history(period=period)
                history[label] = [
                    {"label": date.strftime("%b %d"), "p": round(row["Close"], 2)}
                    for date, row in hist.iterrows()
                ]
            except Exception:
                history[label] = []
        return history