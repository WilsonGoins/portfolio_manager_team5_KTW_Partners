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

    def _format_large_number(self, val: float) -> str:
        """Helper to format large raw numbers into readable financial string values ($3.05T, 48.2M, etc.)."""
        if not val or val == 0:
            return "N/A"

        is_currency = val > 1000  # Simple heuristic for Market Cap vs Volume

        for unit, symbol in [(1_000_000_000_000, 'T'), (1_000_000_000, 'B'), (1_000_000, 'M'), (1_000, 'K')]:
            if abs(val) >= unit:
                formatted = f"{val / unit:.1f}{symbol}"
                return f"${formatted}" if is_currency else formatted
        return f"${val:.2f}" if is_currency else f"{val:.0f}"

    def get_stock_by_ticker(self, ticker: str) -> dict:
        """Method 1: Query for stock by ticker."""
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
            self.logger.error(f"Failed to fetch stock by ticker '{
                              ticker}': {e}", exc_info=True)
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
            self.logger.error(f"Failed to fetch stocks by name '{
                              query}': {e}", exc_info=True)
            return []

    def get_top_movers(self, count: int = 5) -> list[dict]:
        """
        Method 3: Query for the 5 biggest movers.
        """
        try:
            results = yf.screen("day_gainers", count=count)
            quotes = results.get("quotes", [])

            movers = []
            for q in quotes:
                ticker = q.get("symbol")
                if ticker:
                    enriched = self._get_security_details(ticker)
                    if enriched:
                        movers.append(enriched)
            return movers
        except Exception as e:
            self.logger.error(f"Failed to fetch top movers: {
                              e}", exc_info=True)
            return []

    def search_securities(self, query: str, max_results: int = 5) -> list[dict]:
        """Searches for securities matching a query and returns rich SecurityCard-shaped data."""
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
            self.logger.error(f"Failed to search securities for '{
                              query}': {e}", exc_info=True)
            return []

    def _get_security_details(self, ticker: str) -> dict:
        """Builds the full SecurityCard-shaped dict for a single ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            current_price = info.get("currentPrice") or info.get(
                "regularMarketPrice") or 0.0
            previous_close = info.get("previousClose") or current_price

            # Capitalize type nicely (e.g. "EQUITY" -> "Equity")
            raw_type = info.get("quoteType", "Equity")
            formatted_type = raw_type.title() if isinstance(raw_type, str) else "Equity"

            # PE Ratio formatting
            pe = info.get("trailingPE")
            pe_formatted = round(pe, 1) if pe is not None else "N/A"

            return {
                "symbol": ticker.upper(),
                "name": info.get("longName") or info.get("shortName") or ticker.upper(),
                "h_type": formatted_type,
                "curr_price": round(float(current_price), 2),
                "previous_close": round(float(previous_close), 2),
                "change_since_close": round(float(current_price - previous_close), 2),
                "pe_ratio": pe_formatted,
                "market_cap": self._format_large_number(info.get("marketCap", 0)),
                "high_52wk": round(float(info.get("fiftyTwoWeekHigh", current_price)), 2),
                "low_52wk": round(float(info.get("fiftyTwoWeekLow", current_price)), 2),
                "volume": self._format_large_number(info.get("volume", 0)),
                "performanceHistory": self._get_performance_history(stock),
            }
        except Exception as e:
            self.logger.error(f"Failed to get details for '{
                              ticker}': {e}", exc_info=True)
            return None

    def _get_performance_history(self, stock: yf.Ticker) -> dict:
        """Builds the 1W/1M/1Y/YTD chart data SecurityCard expects."""
        ranges = {"1W": "5d", "1M": "1mo", "1Y": "1y", "YTD": "ytd"}
        history = {}
        for label, period in ranges.items():
            try:
                hist = stock.history(period=period)
                history[label] = [
                    {"label": date.strftime("%b %d"), "p": round(
                        float(row["Close"]), 2)}
                    for date, row in hist.iterrows()
                ]
            except Exception:
                history[label] = []
        return history
