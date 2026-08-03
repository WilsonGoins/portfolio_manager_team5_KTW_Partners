import logging
import os
import time
import threading
from datetime import datetime, time as dt_time
from flask import Flask, jsonify, request
from flask_cors import CORS
from db_manager import DBManager
from dotenv import load_dotenv
from finance_manager import FinanceManager
from portfolio_manager import PortfolioManager

load_dotenv()
DB_CONNECTION_STR = os.getenv("DB_CONNECTION_STRING")
UPDATE_PORTFOLIO_VALUE = bool(os.getenv("UPDATE_PORTFOLIO_VALUE")) or False
print(f"UPDATE_PORTFOLIO_VALUE={UPDATE_PORTFOLIO_VALUE}")
PORTFOLIO_VALUE_REFRESH_RATE_S = 3600

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

db_manager = DBManager(
    DB_CONNECTION_STR, flask_logger=app.logger, enable_cache=True)
finance_manager = FinanceManager(flask_logger=app.logger)
portfolio_manager = PortfolioManager(db_manager, finance_manager)


# Refreshing drops the quote cache, so it is the one request that can hit Yahoo
# as fast as somebody can click, and enough of those in a row gets us throttled.
# One real refresh per window; the clicks in between are answered from cache.
_REFRESH_MIN_INTERVAL_SECONDS = 10
_last_refresh_at = None
_refresh_lock = threading.Lock()


def _claim_refresh() -> bool:
    """Whether this request gets to do a real refresh. Records the time when it
    does, so callers must only ask when they intend to go through with it."""
    global _last_refresh_at

    now = time.monotonic()
    with _refresh_lock:
        if (_last_refresh_at is not None
                and now - _last_refresh_at < _REFRESH_MIN_INTERVAL_SECONDS):
            return False

        _last_refresh_at = now
        return True


def _check_market_open(dt: datetime = None) -> bool:
    if dt is None:
        dt = datetime.now()

    is_weekday = dt.weekday() < 5

    start_time = dt_time(9, 0)
    end_time = dt_time(16, 0)
    is_during_hours = start_time <= dt.time() <= end_time

    return is_weekday and is_during_hours


def recurring_portfolio_value_update():
    while True:
        time.sleep(PORTFOLIO_VALUE_REFRESH_RATE_S)
        if _check_market_open():
            try:
                with app.app_context():
                    app.logger.info("Updating portfolio value...")
                    # add only check from market openings
                    new_value = portfolio_manager.update_portfolio_value()[
                        'total_value']
                    app.logger.info(
                        f"Update for portfolio value completed with new value: ${new_value}.")
            except Exception as e:
                app.logger.error(f"Error in background DB job: {
                                 e}", exc_info=True)


if UPDATE_PORTFOLIO_VALUE:
    bg_thread = threading.Thread(
        target=recurring_portfolio_value_update, daemon=True)
    bg_thread.start()


@app.route("/")
def hello_world():
    return jsonify({"message": "Hello, World!", "status": "success"})


@app.route("/api/overview")
def overview():
    """Returns everything the Overview page renders: HoldingsTable, Allocations,
    PortfolioSummary, PortfolioHistory, and TopMovers."""
    try:
        # the navbar's Refresh button means "go and fetch", so it drops the quote
        # cache first rather than being served whatever is still inside its TTL --
        # but no more often than the throttle above allows. A refused refresh
        # still returns the page, just from cache.
        if request.args.get("refresh") == "true" and _claim_refresh():
            finance_manager.empty_cache()

        return jsonify(portfolio_manager.GetOverviewData())
    except Exception as e:
        app.logger.error(f"Failed to get overview data: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch overview data"}), 500


@app.route("/api/transactions")
def transactions():
    try:
        return jsonify(portfolio_manager.GetTransactions())
    except Exception as e:
        app.logger.error(f"Failed to get transactions: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch transactions"}), 500


@app.route("/api/cash")
def cash():
    try:
        return jsonify({"cash": portfolio_manager.GetCashAmount()})
    except Exception as e:
        app.logger.error(f"Failed to get cash amount: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch cash amount"}), 500


@app.route("/api/news")
def get_news():
    """Returns news from yahoo"""
    try:
        return jsonify(portfolio_manager.get_news())
    except Exception as e:
        app.logger.error(f"Failed to fetch news from yahoo: {
                         e}", exc_info=True)
        return jsonify({"error": "Failed to fetch news"}), 500


@app.route("/api/top-movers")
def get_top_movers():
    """Top 5 movers, reshaped to match WatchListCard's expected {symbol, price, change} shape."""
    try:
        movers_data = portfolio_manager.get_top_movers()
        return jsonify(movers_data)
    except Exception as e:
        app.logger.error(f"Failed to get watchlist data: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch watchlist data"}), 500


@app.route("/api/risk")
def risk():
    """The Risk page's data: the portfolio's beta, how it breaks down by holding,
    and how much of the portfolio that beta actually describes."""
    try:
        return jsonify(portfolio_manager.CalculatePortfolioRisk())
    except Exception as e:
        app.logger.error(f"Failed to get risk data: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch risk data"}), 500


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()
    app.logger.info(f"Searching Yahoo for {query}.")
    if not query:
        return jsonify([])

    try:
        # TODO call from portfolio_manager instead of finance_manager
        results = finance_manager.search_securities(query)
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Failed to search securities for '{
            query}': {e}", exc_info=True)
        return jsonify({"error": "Failed to search securities"}), 500


@app.route("/api/analytics/movers")
def analytics_movers():
    """Analytics page: the current holding with the biggest gain and the one
    with the biggest loss, by percent move since yesterday's close."""
    try:
        return jsonify(portfolio_manager.GetBiggestGainerAndLoser())
    except Exception as e:
        app.logger.error(f"Failed to get biggest gainer/loser: {
            e}", exc_info=True)
        return jsonify({"error": "Failed to fetch biggest gainer/loser"}), 500


@app.route("/api/analytics/drawdown")
def analytics_drawdown():
    """Analytics page: the portfolio's single worst decline (max drawdown) and
    single best run (max run-up), found over its full value history."""
    try:
        return jsonify(portfolio_manager.GetDrawdownAndRunup())
    except Exception as e:
        app.logger.error(f"Failed to get drawdown/runup: {
            e}", exc_info=True)
        return jsonify({"error": "Failed to fetch drawdown/runup"}), 500


@app.route("/api/buy", methods=["POST"])
def buy():
    data = request.get_json()
    try:
        ticker, quantity, price = data["ticker"], data["quantity"], data["price"]
    except (KeyError, TypeError):
        return jsonify({"error": "ticker, quantity, and price are required"}), 400

    try:
        portfolio_manager.Buy(ticker, quantity, price)
        return jsonify({"status": "success"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Failed to process buy: {e}", exc_info=True)
        return jsonify({"error": "Failed to process buy"}), 500


@app.route("/api/sell", methods=["POST"])
def sell():
    data = request.get_json()
    try:
        ticker, quantity, price = data["ticker"], data["quantity"], data["price"]
    except (KeyError, TypeError):
        return jsonify({"error": "ticker, quantity, and price are required"}), 400

    try:
        portfolio_manager.Sell(ticker, quantity, price)
        return jsonify({"status": "success"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Failed to process sell: {e}", exc_info=True)
        return jsonify({"error": "Failed to process sell"}), 500
