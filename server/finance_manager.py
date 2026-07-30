import yfinance as yf
import logging
import time
import math
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# Yahoo answers one ticker per request, so the only way to speed up a batch is to
# have several in flight at once. Capped so a large portfolio doesn't open a
# connection per holding and get us rate limited.
_MAX_QUOTE_WORKERS = 8

# How long a quote is reused before we go back to Yahoo for it. Long enough that
# a page load costs nothing when someone just looked, short enough that the
# prices on screen are still today's.
_QUOTE_TTL_SECONDS = 45

# Ceiling on how many entries are held at once. Search caches a security per
# result and its queries come from the user, so without a cap the cache would
# grow with every new ticker anyone ever types.
_MAX_CACHE_ENTRIES = 256


class _TTLCache:
    """A small cache whose entries expire a fixed number of seconds after they
    were stored.

    Entries are written from the quote worker threads, so reads and writes are
    both locked. Expiry is lazy -- an expired entry reads as a miss -- but the
    cache is capped, and going over the cap is what triggers a clear-out, so a
    run of one-off lookups can't grow it without bound.
    """

    def __init__(self, ttl_seconds: float, max_entries: int = _MAX_CACHE_ENTRIES):
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._entries: dict = {}
        self._lock = Lock()

    def get(self, key):
        """The cached value, or None if there isn't a fresh one. Failures are
        never stored, so None is always a miss and never a cached result."""
        with self._lock:
            entry = self._entries.get(key)

        if entry is None:
            return None

        value, stored_at = entry
        return value if time.monotonic() - stored_at <= self._ttl else None

    def set(self, key, value):
        now = time.monotonic()
        with self._lock:
            self._entries[key] = (value, now)
            if len(self._entries) <= self._max_entries:
                return

            # over the cap: drop everything already expired, since an expired
            # entry is dead weight -- it can only ever read as a miss
            self._entries = {k: (v, t) for k, (v, t) in self._entries.items()
                             if now - t <= self._ttl}

            # still over: drop the oldest until we fit
            overflow = len(self._entries) - self._max_entries
            if overflow > 0:
                oldest = sorted(self._entries, key=lambda k: self._entries[k][1])
                for k in oldest[:overflow]:
                    del self._entries[k]

    def clear(self):
        with self._lock:
            self._entries = {}


class FinanceManager:
    """This class is responsible for handling all yahoo finance queries"""

    def __init__(self, flask_logger: logging.Logger):
        self.logger = flask_logger
        self._cache = _TTLCache(_QUOTE_TTL_SECONDS)

    def empty_cache(self):
        """Drops every cached quote, so the next read goes back to Yahoo. Used by
        the overview's manual refresh, which is meant to fetch, not to re-serve."""
        self._cache.clear()

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
        # keyed on the normalised symbol so "aapl" and "AAPL" share one entry.
        # str() keeps a non-string ticker out of the cache lookup and lets it
        # fail below the way it always has, as a caught error rather than here.
        cache_key = ("quote", str(ticker).upper())
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            info = yf.Ticker(ticker).info
            quote = {
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

        # Not raising isn't the same as succeeding: a throttled Yahoo returns a
        # thin payload that parses cleanly with its numbers missing. Caching one
        # of those would serve the same unusable quote for the whole TTL, so it
        # is returned but not stored and the next request fetches again.
        if quote["current_price"] is not None and quote["previous_close"] is not None:
            self._cache.set(cache_key, quote)
        else:
            self.logger.warning(
                f"Incomplete quote for '{ticker}', not caching: {quote}")

        return quote

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
        cached = self._cache.get(("movers", count))
        if cached is not None:
            return cached

        try:
            results = yf.screen("day_gainers", count=count)
            quotes = results.get("quotes", [])

            symbols = [q.get("symbol") for q in quotes if q.get("symbol")]
            movers = self._get_security_details_batch(symbols)
        except Exception as e:
            self.logger.error(f"Failed to fetch top movers: {
                              e}", exc_info=True)
            return []

        self._cache.set(("movers", count), movers)
        return movers

    def search_securities(self, query: str, max_results: int = 5) -> list[dict]:
        query = query.strip()
        if not query:
            return []

        try:
            results = yf.Search(query, max_results=max_results).quotes
            symbols = [r.get("symbol") for r in results if r.get("symbol")]

            return self._get_security_details_batch(symbols)
        except Exception as e:
            self.logger.error(f"Failed to search securities for '{
                              query}': {e}", exc_info=True)
            return []

    def _get_security_details_batch(self, tickers: list[str]) -> list[dict]:
        """Details for several tickers, in the order given.

        Yahoo answers one ticker per request, so these run concurrently -- the
        wait is roughly one round trip rather than one per ticker. Tickers that
        fail are dropped rather than failing the whole batch.
        """
        if not tickers:
            return []

        with ThreadPoolExecutor(
                max_workers=min(len(tickers), _MAX_QUOTE_WORKERS)) as executor:
            details = executor.map(self._get_security_details, tickers)

        return [d for d in details if d is not None]

    def _get_security_details(self, ticker: str) -> dict:
        """Builds the full SecurityCard-shaped dict for a single ticker."""
        cache_key = ("details", str(ticker).upper())
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

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

            details = {
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

        self._cache.set(cache_key, details)
        return details

    def _get_performance_history(self, stock: yf.Ticker) -> dict:
        """Builds chart data by pulling 1 year of history ONCE and slicing in memory."""
        try:
            hist = stock.history(period="1y")
            if hist.empty:
                return {"1W": [], "1M": [], "1Y": [], "YTD": []}

            hist = hist.dropna(subset=["Close"])

            def format_rows(df):
                rows = []
                for idx, row in df.iterrows():
                    close_val = row["Close"]
                    if math.isnan(close_val):
                        continue
                    rows.append({
                        "label": idx.strftime("%b %d"),
                        "p": round(float(close_val), 2)
                    })
                return rows

            now = hist.index[-1]
            hist_1w = hist.tail(5)
            hist_1m = hist.tail(21)
            hist_ytd = hist[hist.index.year == now.year]

            return {
                "1W": format_rows(hist_1w),
                "1M": format_rows(hist_1m),
                "1Y": format_rows(hist),
                "YTD": format_rows(hist_ytd),
            }
        except Exception as e:
            self.logger.error(f"Error building chart history: {e}")
