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

# Daily closes only change once a day (today's isn't final until market close),
# so there's nothing to gain from re-fetching a year of history every 45
# seconds the way a live quote is. Cached separately, and much longer.
_HISTORY_TTL_SECONDS = 6 * 60 * 60

# Ceiling on how many entries are held at once. Search caches a security per
# result and its queries come from the user, so without a cap the cache would
# grow with every new ticker anyone ever types.
_MAX_CACHE_ENTRIES = 256


class _TTLCache:
    """A small cache whose entries expire a 45 seconds after they
    were stored.

    Entries are written from the quote worker threads, so reads and writes are
    both locked. Expiry is lazy so an expired entry reads as a miss, but the
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
            self._entries = {
                k: (v, t) for k, (v, t) in self._entries.items() if now - t <= self._ttl
            }

            # still over: drop the oldest until we fit
            overflow = len(self._entries) - self._max_entries
            if overflow > 0:
                oldest = sorted(
                    self._entries, key=lambda k: self._entries[k][1])
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
        self._history_cache = _TTLCache(_HISTORY_TTL_SECONDS)

    def empty_cache(self) -> None:
        """Clears all cached financial quotes.

        Forces subsequent read requests to bypass local memory and fetch fresh data
        directly from Yahoo Finance. Typically invoked during manual user refreshes
        to guarantee up-to-date data.
        """
        self._cache.clear()

    def _format_large_number(self, val: float) -> str:
        """Formats large numerical values into compact, human-readable financial strings.

        Applies magnitude suffixes (K, M, B, T) and conditionally prefixes currency
        symbols based on standard financial heuristics.

        Args:
            val (float): The raw numeric value to format (e.g., market cap, volume).

        Returns:
            str: The abbreviated string representation (e.g., "$3.1T", "48.2M"),
                or "N/A" if the input value is zero or falsy.
        """
        if not val or val == 0:
            return "N/A"

        is_currency = val > 1000  # Simple heuristic for Market Cap vs Volume

        for unit, symbol in [
            (1_000_000_000_000, "T"),
            (1_000_000_000, "B"),
            (1_000_000, "M"),
            (1_000, "K"),
        ]:
            if abs(val) >= unit:
                formatted = f"{val / unit:.1f}{symbol}"
                return f"${formatted}" if is_currency else formatted
        return f"${val:.2f}" if is_currency else f"{val:.0f}"

    def _extract_beta(self, info: dict) -> float | None:
        """Extracts the beta coefficient from a Yahoo Finance API payload.

        Checks for both equity-style ("beta", 5-year monthly against S&P 500)
        and fund-style ("beta3Year") keys. Validates that the returned value
        can be safely cast to a finite floating-point number.

        Args:
            info (dict): The raw ticker information payload fetched from Yahoo Finance.

        Returns:
            float | None: The numerical beta value if present and finite, or None if
                unusable, non-numeric, infinite, or missing.
        """
        # not `a or b`: a legitimate beta of 0.0 is falsy and would fall through
        beta = info.get("beta")
        if beta is None:
            beta = info.get("beta3Year")

        if beta is None:
            return None

        # a non-numeric beta is Yahoo giving us something unusable rather than a
        # value worth propagating into a weighted average
        try:
            beta = float(beta)
        except (TypeError, ValueError):
            return None

        return beta if math.isfinite(beta) else None

    def get_stock_by_ticker(self, ticker: str) -> dict | None:
        """Fetches stock quote details for a given symbol, with caching support.

        Retrieves market data using yfinance, extracts core stock fields (price,
        name, sector, beta), and stores completed quotes in local cache. Incomplete
        quotes resulting from throttled or partial API responses are returned
        without being cached to ensure future attempts can retry fetching.

        Args:
            ticker (str): The stock or ETF symbol to look up (e.g., "AAPL").

        Returns:
            dict | None: A dictionary containing quote data (ticker, current_price,
                name, stock_type, previous_close, sector, beta) if successful,
                or None if an exception occurs during the fetch.
        """
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
                "current_price": info.get("currentPrice")
                or info.get("regularMarketPrice"),
                "name": info.get("longName") or info.get("shortName"),
                "stock_type": info.get("quoteType"),
                "previous_close": info.get("previousClose"),
                # ETFs don't carry a GICS "sector" the way equities do, so fall
                # back to Yahoo's fund "category" (e.g. "Large Growth"), and
                # finally to "Other" for anything with neither (e.g. cash).
                "sector": info.get("sector") or info.get("category") or "Other",
                "beta": self._extract_beta(info),
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch stock by ticker '{
                ticker}': {e}", exc_info=True)
            return None

        # Not raising isn't the same as succeeding: a throttled Yahoo returns a
        # thin payload that parses cleanly with its numbers missing. Caching one
        # of those would serve the same unusable quote for the whole TTL, so it
        # is returned but not stored and the next request fetches again.
        #
        # Beta deliberately isn't part of this test. Plenty of securities have no
        # beta on Yahoo even in a complete payload, so requiring one would mean
        # never caching those tickers and re-fetching them on every single read.
        if quote["current_price"] is not None and quote["previous_close"] is not None:
            self._cache.set(cache_key, quote)
        else:
            self.logger.warning(
                f"Incomplete quote for '{ticker}', not caching: {quote}"
            )

        return quote

    def get_stocks_by_tickers(self, tickers: list[str]) -> dict[str, dict | None]:
        """Fetches quote details for multiple tickers concurrently.

        Executes queries using a thread pool to optimize fetch times down to a
        single concurrent round trip. Deduplicates inputs prior to fetching.

        Args:
            tickers (list[str]): List of stock or ETF symbols to look up.

        Returns:
            dict[str, dict | None]: A dictionary mapping each original input ticker
                symbol to its corresponding quote dictionary, or None if the individual
                fetch failed.
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
            max_workers=min(len(unique_tickers), _MAX_QUOTE_WORKERS)
        ) as executor:
            futures = {
                ticker: executor.submit(self.get_stock_by_ticker, ticker)
                for ticker in unique_tickers
            }

            for ticker, future in futures.items():
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    # get_stock_by_ticker swallows its own failures, so this is
                    # something unexpected -- keep the other tickers' results
                    self.logger.error(
                        f"Failed to fetch stock by ticker '{ticker}': {e}",
                        exc_info=True,
                    )
                    results[ticker] = None

        return results

    def get_stock_by_name(self, name: str) -> list[dict]:
        """Performs a fuzzy search for securities matching a name or query string.

        Queries Yahoo Finance for matching ticker symbols and retrieves complete quote
        data for each valid result.

        Args:
            name (str): The search term, such as a company name or partial ticker.

        Returns:
            list[dict]: A list of quote dictionaries for matching securities, ranked by
                relevance. Returns an empty list if the query is empty, no results
                are found, or an error occurs.
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

    def get_index_history(self, ticker: str = "^GSPC") -> dict[str, float]:
        """Retrieves 1-year historical daily closing prices for a market index.

        Fetches daily price history and formats the dates as string keys for fast,
        direct lookup. Results are stored in the index history cache upon success.

        Args:
            ticker (str, optional): The symbol for the market index to look up.
                Defaults to "^GSPC" (S&P 500).

        Returns:
            dict[str, float]: A mapping of dates in "YYYY-MM-DD" format to their
                corresponding rounded closing prices. Returns an empty dictionary
                on failure or if no data is available.
        """
        cache_key = ("index_history", ticker.upper())
        cached = self._history_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            hist = yf.Ticker(ticker).history(period="1y")
            if hist.empty:
                return {}

            hist = hist.dropna(subset=["Close"])
            closes = {
                idx.strftime("%Y-%m-%d"): round(float(row["Close"]), 2)
                for idx, row in hist.iterrows()
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch index history for '{
                ticker}': {e}", exc_info=True)
            return {}

        self._history_cache.set(cache_key, closes)
        return closes

    def get_top_movers(self, count: int = 5) -> list[dict]:
        """Fetches the top market gainers for the current trading day.

        Uses Yahoo Finance screeners to retrieve top daily gainers, fetches full
        quote details for the batch, and caches the result.

        Args:
            count (int, optional): The number of top moving securities to retrieve.
                Defaults to 5.

        Returns:
            list[dict]: A list of quote dictionaries representing the top daily
                gainers. Returns an empty list if fetching fails.
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
        """Searches for securities by name or symbol and retrieves batch quote data.

        Executes a search query against Yahoo Finance and fetches comprehensive details
        for up to `max_results` matching tickers.

        Args:
            query (str): The search term (e.g., ticker symbol or company name).
            max_results (int, optional): Maximum number of search results to return.
                Defaults to 5.

        Returns:
            list[dict]: A list of quote dictionaries for matching securities.
                Returns an empty list if the query is blank or search fails.
        """
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
        """Fetches comprehensive security details for a batch of tickers concurrently.

        Executes queries using a thread pool to retrieve detailed data in parallel.
        Filters out any tickers that fail to resolve or return None.

        Args:
            tickers (list[str]): List of stock or ETF symbols to retrieve details for.

        Returns:
            list[dict]: A list of SecurityCard-shaped dictionaries containing
                detailed security data for all successfully fetched tickers.
        """
        if not tickers:
            return []

        with ThreadPoolExecutor(
            max_workers=min(len(tickers), _MAX_QUOTE_WORKERS)
        ) as executor:
            details = executor.map(self._get_security_details, tickers)

        return [d for d in details if d is not None]

    def _get_security_details(self, ticker: str) -> dict | None:
        """Constructs a detailed SecurityCard dictionary for a single ticker.

        Retrieves raw data from Yahoo Finance, formats key financial metrics
        (such as P/E ratio, market cap, 52-week ranges, volume, and performance
        history), and caches the resulting dictionary upon success.

        Args:
            ticker (str): The stock or ETF symbol to query.

        Returns:
            dict | None: A dictionary containing formatted security details,
                or None if an error occurs during processing.
        """
        cache_key = ("details", str(ticker).upper())
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            current_price = (
                info.get("currentPrice") or info.get(
                    "regularMarketPrice") or 0.0
            )
            previous_close = info.get("previousClose") or current_price

            # Capitalize type nicely (e.g. "EQUITY" -> "Equity")
            raw_type = info.get("quoteType", "Equity")
            formatted_type = raw_type.title() if isinstance(raw_type, str) else "Equity"

            # PE Ratio formatting
            pe = info.get("trailingPE")
            pe_formatted = round(pe, 1) if pe is not None else "N/A"

            description = (
                info.get("longBusinessSummary") or info.get(
                    "description") or None
            )

            details = {
                "symbol": ticker.upper(),
                "name": info.get("longName") or info.get("shortName") or ticker.upper(),
                "h_type": formatted_type,
                "description": description,
                "curr_price": round(float(current_price), 2),
                "previous_close": round(float(previous_close), 2),
                "change_since_close": round(float(current_price - previous_close), 2),
                "pe_ratio": pe_formatted,
                "market_cap": self._format_large_number(info.get("marketCap", 0)),
                "high_52wk": round(
                    float(info.get("fiftyTwoWeekHigh", current_price)), 2
                ),
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

        self._cache.set(cache_key, details)
        return details

    def _get_performance_history(self, stock: yf.Ticker) -> dict[str, list[dict]]:
        """Constructs historical price chart data split into multiple timeframes.

        Pulls 1 year of historical data once and slices it in memory to generate
        timeframe series for 1 week, 1 month, 1 year, and year-to-date (YTD).

        Args:
            stock (yf.Ticker): The yfinance Ticker object to query.

        Returns:
            dict[str, list[dict]]: A dictionary mapping timeframes ("1W", "1M", "1Y", "YTD")
                to lists of formatted point records containing "label" (date) and "p" (price).
        """
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
                    rows.append(
                        {
                            "label": idx.strftime("%b %d"),
                            "p": round(float(close_val), 2),
                        }
                    )
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

    def get_news(self, limit: int = 5) -> list[dict]:
        """Fetches market news articles formatted for UI card consumption.

        Iterates through current market movers and fallback indices to gather unique
        news articles, deduplicating by URL until the requested limit is reached.

        Args:
            limit (int, optional): Maximum number of news stories to return.
                Defaults to 5.

        Returns:
            list[dict]: A list of news article dictionaries containing title, publisher,
                url, image_url, and ticker metadata.
        """
        # ^GSPTSE is the Toronto index; "TSX" isn't a symbol Yahoo answers to
        fallback_tickers = ["SPY", "AAPL", "MSFT", "NVDA", "^GSPTSE"]
        results = yf.screen("day_gainers", count=limit)
        quotes = results.get("quotes", [])

        candidate_tickers = [q.get("symbol") for q in quotes]
        candidate_tickers.extend(fallback_tickers)

        final_res = []  # news stories to return
        seen_urls = set()  # urls of stories we've fully added to final_res

        for symbol in candidate_tickers:
            if len(final_res) >= limit:
                break
            if not symbol:
                continue

            ticker = symbol.strip().upper()

            try:
                stories = yf.Ticker(ticker).news or []
            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch news for '{ticker}': {e}")
                continue

            for news_item in stories:
                content = news_item.get("content", news_item)
                title = content.get("title")
                link = content.get("canonicalUrl", {}).get(
                    "url") or content.get("link")

                if not (title and link):  # if nothing to show, go to next story
                    continue

                if link in seen_urls:  # check if we already added this story
                    continue

                provider = content.get("provider", {}).get(
                    "displayName"
                ) or content.get("publisher", "Yahoo Finance")

                image_url = None
                thumbnail_data = content.get(
                    "thumbnail") or news_item.get("thumbnail")

                if isinstance(thumbnail_data, dict):
                    resolutions = thumbnail_data.get("resolutions", [])
                    if resolutions:
                        image_url = resolutions[0].get("url")
                    else:
                        image_url = thumbnail_data.get("url")

                seen_urls.add(link)
                final_res.append(
                    {
                        "title": title,
                        "publisher": provider,
                        "url": link,
                        "image_url": image_url,
                        "ticker": ticker,
                    }
                )
                break  # exit iteration, onto the next

        return final_res
