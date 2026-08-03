"""Integration tests for the backend, one section per API endpoint.

Each test sends a request through the Flask app and checks the JSON that comes
back, so a single test covers api.py and portfolio_manager.py together. The
portfolio behind them is the one described in conftest.py.
"""

import pytest


# ==========================================================================
# GET /api/overview -- everything the Overview page renders
# ==========================================================================

class TestOverview:
    # All seven sections are present, so a missing one shows up here rather
    # than as a blank card on the page.
    def test_returns_every_section_the_page_needs(self, client):
        data = client.get("/api/overview").get_json()

        assert set(data) == {"HoldingsTable", "Allocations",
                             "AllocationsBySector", "PortfolioSummary",
                             "PortfolioHistory", "TopMovers", "LastUpdated"}

    # Cash is folded into the holdings table as its own first row instead of
    # being left out of the list.
    def test_the_holdings_table_leads_with_cash(self, client):
        holdings = client.get("/api/overview").get_json()["HoldingsTable"]

        assert holdings[0]["name"] == "Cash"
        assert holdings[0]["market_value"] == 5000.0

    # A holding's share count is multiplied by its live Yahoo price to get the
    # market value shown in the table.
    def test_each_holding_is_priced_at_its_current_quote(self, client):
        holdings = client.get("/api/overview").get_json()["HoldingsTable"]

        aapl = next(h for h in holdings if h["symbol"] == "AAPL")
        assert aapl["num_shares"] == 10
        assert aapl["curr_price"] == 200.0
        assert aapl["market_value"] == 2000.0     # 10 shares x $200

    # Today's move is measured against yesterday's close, and reported in both
    # dollars and percent.
    def test_the_day_change_is_measured_from_yesterdays_close(self, client):
        holdings = client.get("/api/overview").get_json()["HoldingsTable"]

        aapl = next(h for h in holdings if h["symbol"] == "AAPL")
        assert aapl["change_since_close"] == 100.0             # 10 x $10
        assert aapl["change_pct_since_close"] == pytest.approx(5.263, rel=1e-3)

    # Holdings are grouped by asset type, and each group's total value and
    # share of the portfolio are correct.
    def test_allocations_are_shares_of_the_17000_total(self, client):
        allocations = client.get("/api/overview").get_json()["Allocations"]

        by_label = {a["label"]: a for a in allocations}
        assert by_label["Cash"]["market_value"] == 5000.0
        assert by_label["EQUITY"]["market_value"] == 2000.0
        assert by_label["ETF"]["market_value"] == 10000.0
        assert by_label["ETF"]["allocation_pct"] == pytest.approx(58.82, rel=1e-3)

    # Nothing is double-counted or dropped when the percentages are worked out.
    def test_allocations_add_up_to_one_hundred_percent(self, client):
        allocations = client.get("/api/overview").get_json()["Allocations"]

        total = sum(a["allocation_pct"] for a in allocations)
        assert total == pytest.approx(100.0)

    # The second breakdown groups the same holdings by Yahoo sector rather
    # than by asset type, which is what the Allocation card's toggle switches
    # between.
    def test_the_same_holdings_regroup_by_sector(self, client):
        data = client.get("/api/overview").get_json()

        labels = [a["label"] for a in data["AllocationsBySector"]]
        assert labels == ["Cash", "Large Blend", "Technology"]

    # The headline numbers come from the newest stored snapshot, not an older
    # row further down the table.
    def test_the_summary_is_the_most_recent_stored_snapshot(self, client):
        summary = client.get("/api/overview").get_json()["PortfolioSummary"]

        assert summary["total_value"] == 12000.0
        assert summary["day_change"] == -300.0

    # The chart series is reversed into chronological order, since the
    # database hands snapshots back newest-first.
    def test_the_history_runs_oldest_first(self, client):
        history = client.get("/api/overview").get_json()["PortfolioHistory"]

        dates = [point["date"] for point in history]
        assert dates == sorted(dates)
        assert history[0]["value"] == 15000.0

    # Each history point is matched to the S&P 500's close for that date, so
    # the chart can draw a benchmark line beside the portfolio's.
    def test_the_history_carries_the_benchmark_alongside_it(self, client):
        history = client.get("/api/overview").get_json()["PortfolioHistory"]

        assert history[0]["benchmark_value"] == 4700.0

    # Raw quotes are converted into the {symbol, price, change} shape the
    # watchlist renders, with change as a percentage.
    def test_the_watchlist_is_reshaped_for_the_card(self, client):
        movers = client.get("/api/overview").get_json()["TopMovers"]

        # $50 -> $55 is a 10% move
        assert movers == [{"symbol": "GME", "name": "GameStop",
                           "price": 55.0, "change": pytest.approx(10.0)}]

    # ?refresh=true clears the cached quotes first, so the navbar's Refresh
    # button really goes back to Yahoo.
    def test_a_refresh_drops_the_quote_cache_first(self, client, finance):
        client.get("/api/overview?refresh=true")

        assert finance.cache_emptied == 1

    # An ordinary page load is happy with whatever is already cached, rather
    # than re-fetching every quote on every visit.
    def test_an_ordinary_load_leaves_the_quote_cache_alone(self, client,
                                                           finance):
        client.get("/api/overview")

        assert finance.cache_emptied == 0

    # A database error becomes a clean 500 with a generic message instead of
    # leaking the underlying exception to the browser.
    def test_a_database_failure_is_a_500(self, client, db):
        def boom():
            raise RuntimeError("connection lost")
        db.get_holdings = boom

        response = client.get("/api/overview")

        assert response.status_code == 500
        assert response.get_json() == {"error": "Failed to fetch overview data"}


# ==========================================================================
# GET /api/cash and /api/transactions
# ==========================================================================

class TestCashAndTransactions:
    # The balance comes back wrapped in an object, which is the shape the
    # frontend reads it out of.
    def test_cash_returns_the_balance(self, client):
        response = client.get("/api/cash")

        assert response.status_code == 200
        assert response.get_json() == {"cash": 5000.0}

    # Stored transactions are mapped into the date/ticker/quantity/price/
    # action rows the Transactions table expects.
    def test_transactions_returns_the_ledger(self, client):
        transactions = client.get("/api/transactions").get_json()

        assert len(transactions) == 2
        assert transactions[0]["ticker"] == "AAPL"
        assert transactions[0]["action"] == "buy"
        assert transactions[0]["quantity"] == 10

    # A database error on this endpoint is caught and reported as a 500 rather
    # than crashing the request.
    def test_a_database_failure_is_a_500(self, client, db):
        def boom():
            raise RuntimeError("connection lost")
        db.get_transactions = boom

        response = client.get("/api/transactions")

        assert response.status_code == 500


# ==========================================================================
# POST /api/buy
# ==========================================================================

class TestBuy:
    # Buying a security we don't already hold creates the holding.
    def test_opening_a_new_position(self, client, db):
        response = client.post("/api/buy",
                               json={"ticker": "NVDA", "quantity": 5,
                                     "price": 100.0})

        assert response.status_code == 200
        assert db.get_holding("NVDA").quantity_shares == 5

    # A brand-new holding gets its name and asset type from the Yahoo quote
    # rather than being stored blank.
    def test_a_new_position_takes_its_name_and_type_from_yahoo(self, client,
                                                               db):
        client.post("/api/buy",
                    json={"ticker": "NVDA", "quantity": 5, "price": 100.0})

        assert db.get_holding("NVDA").name == "NVIDIA Corp"
        assert db.get_holding("NVDA").h_type == "EQUITY"

    # A second purchase of the same security adds to the existing share count
    # instead of creating a duplicate row.
    def test_buying_more_of_a_held_position_adds_to_it(self, client, db):
        client.post("/api/buy",
                    json={"ticker": "AAPL", "quantity": 5, "price": 200.0})

        assert db.get_holding("AAPL").quantity_shares == 15

    # The full cost of the purchase is taken out of the cash balance.
    def test_the_cost_comes_out_of_cash(self, client, db):
        client.post("/api/buy",
                    json={"ticker": "NVDA", "quantity": 5, "price": 100.0})

        assert db.cash == 4500.0      # $5,000 - (5 x $100)

    # The buy is recorded in the ledger, so it turns up on the Transactions
    # page afterwards.
    def test_the_purchase_is_written_to_the_ledger(self, client):
        client.post("/api/buy",
                    json={"ticker": "NVDA", "quantity": 5, "price": 100.0})

        latest = client.get("/api/transactions").get_json()[-1]
        assert latest["ticker"] == "NVDA"
        assert latest["action"] == "buy"
        assert latest["quantity"] == 5

    # An order costing more than the account holds is rejected with a 400, and
    # no money is spent.
    def test_buying_beyond_the_cash_balance_is_refused(self, client, db):
        response = client.post("/api/buy",
                               json={"ticker": "AAPL", "quantity": 100,
                                     "price": 200.0})

        assert response.status_code == 400
        assert response.get_json() == {
            "error": "insufficient cash to complete this purchase"}
        assert db.cash == 5000.0      # nothing was spent

    # An order for zero or fewer shares is rejected.
    def test_a_non_positive_quantity_is_refused(self, client):
        response = client.post("/api/buy",
                               json={"ticker": "AAPL", "quantity": 0,
                                     "price": 200.0})

        assert response.status_code == 400
        assert "positive number of shares" in response.get_json()["error"]

    # A symbol Yahoo can't price is rejected rather than stored as an
    # untradeable holding that would break the Overview page later.
    def test_a_ticker_yahoo_does_not_recognise_is_refused(self, client):
        response = client.post("/api/buy",
                               json={"ticker": "NOTREAL", "quantity": 1,
                                     "price": 1.0})

        assert response.status_code == 400
        assert "valid security" in response.get_json()["error"]

    # An incomplete request body is rejected at the route, before it reaches
    # the portfolio.
    def test_a_request_missing_a_field_is_refused(self, client):
        response = client.post("/api/buy", json={"ticker": "AAPL"})

        assert response.status_code == 400
        assert response.get_json() == {
            "error": "ticker, quantity, and price are required"}


# ==========================================================================
# POST /api/sell
# ==========================================================================

class TestSell:
    # Selling some of a position leaves the rest of it in place.
    def test_selling_part_of_a_position_reduces_it(self, client, db):
        response = client.post("/api/sell",
                               json={"ticker": "AAPL", "quantity": 4,
                                     "price": 200.0})

        assert response.status_code == 200
        assert db.get_holding("AAPL").quantity_shares == 6

    # Selling every share deletes the holding rather than leaving a row with
    # zero shares in the table.
    def test_selling_the_whole_position_closes_it(self, client, db):
        client.post("/api/sell",
                    json={"ticker": "AAPL", "quantity": 10, "price": 200.0})

        assert db.get_holding("AAPL") is None

    # The proceeds of the sale are added to the cash balance.
    def test_the_proceeds_go_into_cash(self, client, db):
        client.post("/api/sell",
                    json={"ticker": "AAPL", "quantity": 4, "price": 200.0})

        assert db.cash == 5800.0      # $5,000 + (4 x $200)

    # The sale is recorded in the ledger and marked as a sell, not a buy.
    def test_the_sale_is_written_to_the_ledger(self, client):
        client.post("/api/sell",
                    json={"ticker": "AAPL", "quantity": 4, "price": 200.0})

        latest = client.get("/api/transactions").get_json()[-1]
        assert latest["ticker"] == "AAPL"
        assert latest["action"] == "sell"

    # Selling more shares than are held is rejected, and the position is left
    # exactly as it was.
    def test_selling_more_than_is_held_is_refused(self, client, db):
        response = client.post("/api/sell",
                               json={"ticker": "AAPL", "quantity": 50,
                                     "price": 200.0})

        assert response.status_code == 400
        assert "cannot sell more shares" in response.get_json()["error"]
        assert db.get_holding("AAPL").quantity_shares == 10

    # Selling a security that isn't in the portfolio at all is rejected.
    def test_selling_something_we_do_not_hold_is_refused(self, client):
        response = client.post("/api/sell",
                               json={"ticker": "NVDA", "quantity": 1,
                                     "price": 100.0})

        assert response.status_code == 400

    # An incomplete request body is rejected the same way it is on /api/buy.
    def test_a_request_missing_a_field_is_refused(self, client):
        response = client.post("/api/sell", json={"quantity": 1})

        assert response.status_code == 400


# ==========================================================================
# GET /api/risk
# ==========================================================================

class TestRisk:
    # The portfolio's beta is each holding's beta weighted by how much money
    # is in it.
    def test_beta_is_the_holdings_weighted_average(self, client):
        risk = client.get("/api/risk").get_json()

        # cash 0.0, AAPL 1.2 on $2,000, SPY 1.0 on $10,000, over $17,000
        assert risk["portfolio_beta"] == pytest.approx(0.7294, rel=1e-3)

    # That beta is turned into the plain-language bucket the UI puts on its
    # chip.
    def test_the_beta_is_labelled_in_plain_language(self, client):
        risk = client.get("/api/risk").get_json()

        assert risk["risk_level"] == "Conservative"

    # Every holding gets its own row in the breakdown, cash included.
    def test_every_holding_gets_a_row_including_cash(self, client):
        risk = client.get("/api/risk").get_json()

        symbols = {row["symbol"] for row in risk["holdings"]}
        assert symbols == {"--", "AAPL", "SPY"}

    # Cash is treated as zero-beta, so it contributes nothing to market risk.
    def test_cash_carries_no_market_risk(self, client):
        risk = client.get("/api/risk").get_json()

        cash = next(r for r in risk["holdings"] if r["symbol"] == "--")
        assert cash["beta"] == 0.0
        assert cash["contribution"] == 0

    # Rows are sorted by contribution, so the biggest sources of risk are at
    # the top of the card.
    def test_the_biggest_source_of_risk_leads_the_list(self, client):
        risk = client.get("/api/risk").get_json()

        contributions = [row["contribution"] for row in risk["holdings"]]
        assert contributions == sorted(contributions, reverse=True)

    # When Yahoo has a beta for everything, coverage is 100% and nothing is
    # reported as unpriced.
    def test_coverage_is_total_when_every_holding_has_a_beta(self, client):
        risk = client.get("/api/risk").get_json()

        assert risk["coverage_pct"] == pytest.approx(100.0)
        assert risk["total_value"] == 17000.0
        assert risk["unpriced"] == []


# ==========================================================================
# GET /api/analytics/movers and /api/analytics/drawdown
# ==========================================================================

class TestAnalytics:
    # The best and worst holdings are picked by percentage move, not by dollar
    # move.
    def test_the_biggest_gainer_and_loser_are_picked_by_percent(self, client):
        movers = client.get("/api/analytics/movers").get_json()

        assert movers["biggest_gainer"]["symbol"] == "AAPL"   # +5.26%
        assert movers["biggest_loser"]["symbol"] == "SPY"     # flat

    # Each side carries the price and percentage the card prints.
    def test_the_gainer_carries_the_numbers_the_card_shows(self, client):
        gainer = client.get("/api/analytics/movers").get_json()["biggest_gainer"]

        assert gainer["curr_price"] == 200.0
        assert gainer["change_pct_since_close"] == pytest.approx(5.263,
                                                                 rel=1e-3)

    # The worst peak-to-trough fall in the value history is found, along with
    # the dates on either end of it.
    def test_the_worst_decline_is_found_in_the_history(self, client):
        drawdown = client.get("/api/analytics/drawdown").get_json()["drawdown"]

        # $15,000 on Jul 1 down to $12,000 on Jul 15
        assert drawdown["pct"] == pytest.approx(-20.0)
        assert drawdown["peak_value"] == 15000.0
        assert drawdown["peak_date"] == "2026-07-01"
        assert drawdown["trough_value"] == 12000.0
        assert drawdown["trough_date"] == "2026-07-15"
        assert drawdown["decline_days"] == 14

    # The best trough-to-peak climb is found the same way, ending at the
    # portfolio's live value rather than at the last stored snapshot.
    def test_the_best_climb_is_found_too(self, client):
        runup = client.get("/api/analytics/drawdown").get_json()["runup"]

        # $12,000 back up to today's live $17,000
        assert runup["trough_value"] == 12000.0
        assert runup["peak_value"] == 17000.0
        assert runup["pct"] == pytest.approx(41.667, rel=1e-3)

    # A portfolio sitting at the top of its best run is flagged as being at a
    # new high.
    def test_a_portfolio_at_its_peak_is_reported_as_such(self, client):
        runup = client.get("/api/analytics/drawdown").get_json()["runup"]

        assert runup["at_new_high"] is True

    # With too few snapshots to compare, both cards get null instead of an
    # error.
    def test_a_portfolio_with_no_history_reports_neither(self, client, db):
        db.portfolio_values = []

        data = client.get("/api/analytics/drawdown").get_json()

        assert data == {"drawdown": None, "runup": None}


# ==========================================================================
# GET /api/search, /api/news, /api/top-movers
# ==========================================================================

class TestYahooEndpoints:
    # A search passes the query through to Yahoo and returns the matches.
    def test_search_returns_the_matches(self, client):
        response = client.get("/api/search?q=apple")

        assert response.status_code == 200
        assert response.get_json()[0]["symbol"] == "AAPL"

    # An empty query short-circuits to an empty list without calling Yahoo at
    # all.
    def test_an_empty_search_asks_yahoo_nothing(self, client):
        response = client.get("/api/search")

        assert response.get_json() == []

    # The news endpoint returns the stories the Explore page lists.
    def test_news_returns_the_stories(self, client):
        stories = client.get("/api/news").get_json()

        assert stories[0]["title"] == "Markets rally"

    # The top-movers endpoint returns the screened securities Explore shows as
    # cards.
    def test_top_movers_returns_the_screened_securities(self, client):
        movers = client.get("/api/top-movers").get_json()

        assert movers[0]["symbol"] == "GME"

    # A Yahoo failure (a throttled request, say) becomes a 500 rather than an
    # unhandled exception.
    def test_a_yahoo_failure_is_a_500(self, client, finance):
        def boom(query, max_results=5):
            raise RuntimeError("throttled")
        finance.search_securities = boom

        response = client.get("/api/search?q=apple")

        assert response.status_code == 500
        assert response.get_json() == {"error": "Failed to search securities"}
