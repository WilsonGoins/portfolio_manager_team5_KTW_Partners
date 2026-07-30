import logging
from contextlib import contextmanager
from typing import Any
from db_items import Holding, Transaction, PortfolioValue
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from datetime import datetime


_CASH_PK = "user"


class DBManager():
    """Handles all db related needs"""

    def __init__(
            self,
            conn_str: str,
            flask_logger: logging.Logger,
            enable_cache: bool = True):
        self.logger = flask_logger
        self._enable_cache = enable_cache
        self._cache: dict[str, Any] = {}
        self._pool = ConnectionPool(
            conn_str,
            kwargs={"row_factory": dict_row},
            check=ConnectionPool.check_connection,
            min_size=1,
            max_size=4,
            max_lifetime=5 * 60,
            open=False)

        try:
            self._pool.open(wait=True, timeout=10)
            self.logger.info("Database connected successfully.")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {
                              e}", exc_info=True)
            self.logger.error(
                "WE SHOULD RERAISE HERE TO BE HANDLED IN API CONTROLLER")

    @contextmanager
    def _cursor(self):
        """Checks a connection out of the pool and yields a cursor on it.

        The transaction is committed when the block exits normally and rolled
        back if it raises, so no connection is ever left idle in transaction.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                yield cur

    def empty_cache(self, key: str = None):
        if key is None:
            self._cache = {}
            self._enable_cache and self.logger.debug(
                "Cache[DELETE] Cleared all keys.")
        else:
            self._cache.pop(key, None)
            self._enable_cache and self.logger.debug(
                f"Cache[DELETE] Cleared cache for key: {key}")

    def _empty_holding_cache(self, ticker_symbol: str):
        """Clears both places a holding is cached: the full list, and its own
        per-ticker entry.

        Both have to go. Dropping only the list leaves get_holding handing back a
        row that has since changed quantity or been deleted outright -- and a
        deleted one still reads as "we hold this", so Buy would update a row that
        is no longer there instead of re-adding it.
        """
        self.empty_cache(key="holdings")
        self.empty_cache(key=f"holding:{ticker_symbol}")

    # -------------------- CASH --------------------

    def get_cash(self) -> float | None:
        with self._cursor() as cur:
            cur.execute("SELECT value FROM cash WHERE uid = %s", [_CASH_PK])
            cash_row = cur.fetchone()
            cash_value: float = float(
                cash_row["value"]) if cash_row is not None else None

            return cash_value

    def set_cash(self, new_value: float) -> float:
        sql_str = """
            INSERT INTO cash (uid, value)
            VALUES (%s, %s)
            ON CONFLICT (uid)
            DO UPDATE SET value = EXCLUDED.value;
        """
        with self._cursor() as cur:
            cur.execute(sql_str, [_CASH_PK, new_value])
        return new_value

    # -------------------- READ --------------------

    def get_portfolio_value(self, p_date: datetime) -> PortfolioValue:
        if self._enable_cache and f"pv:{p_date}" in self._cache:
            self.logger.debug(f"Cache[HIT] \"pv:{p_date}\": {
                              self._cache[f"pv:{p_date}"]}")
            return self._cache[f"pv:{p_date}"]
        else:
            self.logger.debug(f"Cache[MISS] \"pv:{p_date}\"")

        with self._cursor() as cur:
            cur.execute("SELECT * FROM portfolio_value WHERE p_date = %s",
                        [p_date])

            pv_dict = cur.fetchone()
            if pv_dict is None:
                return None

            pv = PortfolioValue.from_dict(pv_dict)
            if self._enable_cache:
                self._cache[f"pv:{p_date}"] = pv
                self.logger.debug(f"CACHE[UPDATE] \"pv:{
                    p_date}\": {pv}")

            return pv

    def get_portfolio_values(self) -> list[PortfolioValue]:
        if self._enable_cache and "portfolio_values" in self._cache:
            self.logger.debug(f"Cache[HIT] \"portfolio_values\": {
                              self._cache["portfolio_values"]}")
            return self._cache["portfolio_values"]
        else:
            self.logger.debug("Cache[MISS] \"portfolio_values\"")

        with self._cursor() as cur:
            cur.execute("SELECT * FROM portfolio_value")

            portfolio_values: list[PortfolioValue] = []
            for pv_dict in cur.fetchall():
                portfolio_values.append(PortfolioValue.from_dict(pv_dict))

            if self._enable_cache:
                self._cache["portfolio_values"] = portfolio_values
                self.logger.debug(f"CACHE[UPDATE] \"portfolio_values\": {
                                  portfolio_values}")

            return portfolio_values

    def get_holding(self, ticker_symbol: str) -> Holding | None:
        if self._enable_cache and f"holding:{ticker_symbol}" in self._cache:
            self.logger.debug(f"Cache[HIT] \"holding:{ticker_symbol}\": {
                              self._cache[ticker_symbol]}")
            return self._cache[f"holding:{ticker_symbol}"]
        else:
            self.logger.debug(f"Cache[MISS] \"holding:{ticker_symbol}\"")

        with self._cursor() as cur:
            cur.execute("SELECT * FROM holdings WHERE ticker = %s",
                        [ticker_symbol])

            holding_dict = cur.fetchone()
            if holding_dict is None:
                return None

            holding = Holding.from_dict(holding_dict)
            if self._enable_cache:
                self._cache[f"holding:{ticker_symbol}"] = holding
                self.logger.debug(f"CACHE[UPDATE] \"holding:{
                    ticker_symbol}\": {holding}")

            return holding

    def get_holdings(self) -> list[Holding]:
        if self._enable_cache and "holdings" in self._cache:
            self.logger.debug(f"Cache[HIT] \"holdings\": {
                              self._cache["holdings"]}")
            return self._cache["holdings"]
        else:
            self.logger.debug("Cache[MISS] \"holdings\"")

        with self._cursor() as cur:
            cur.execute("SELECT * FROM holdings")

            holdings: list[Holding] = []
            for holding_dict in cur.fetchall():
                holdings.append(Holding.from_dict(holding_dict))

            if self._enable_cache:
                self._cache["holdings"] = holdings
                self.logger.debug(
                    f"CACHE[UPDATE] \"holdings\": {holdings}")

            return holdings

    def get_transaction(self, trans_id: int) -> Transaction | None:
        # TODO: delete this? how would we even query b the transaction id? they are set by the db and random
        if self._enable_cache and f"transaction:{trans_id}" in self._cache:
            self.logger.debug(f"Cache[HIT] \"transaction:{trans_id}\": {
                              self._cache[trans_id]}")
            return self._cache[f"transaction:{trans_id}"]
        else:
            self.logger.debug(f"Cache[MISS] \"transaction:{trans_id}\"")

        with self._cursor() as cur:
            cur.execute("SELECT * FROM transactions WHERE trans_id = %s",
                        [trans_id])

            transaction_dict = cur.fetchone()
            if transaction_dict is None:
                return None

            transaction = Transaction.from_dict(transaction_dict)
            if self._enable_cache:
                self._cache[f"transaction:{trans_id}"] = transaction
                self.logger.debug(f"CACHE[UPDATE] \"transaction:{
                    trans_id}\": {transaction}")

            return transaction

    def get_transactions(self) -> list[Transaction]:
        if self._enable_cache and "transactions" in self._cache:
            self.logger.debug(f"Cache[HIT] \"transactions\": {
                              self._cache["transactions"]}")
            return self._cache["transactions"]
        else:
            self.logger.debug("Cache[MISS] \"transactions\"")

        with self._cursor() as cur:
            cur.execute("SELECT * FROM transactions")

            transactions: list[Transaction] = []
            for transaction_dict in cur.fetchall():
                transactions.append(Transaction.from_dict(transaction_dict))

            if self._enable_cache:
                self._cache["transactions"] = transactions
                self.logger.debug(
                    f"CACHE[UPDATE] \"transactions\": {transactions}")
            return transactions

    # -------------------- CREATE --------------------

    def add_holding(self, holding: Holding) -> list[Holding]:
        with self._cursor() as cur:
            cur.execute("INSERT INTO holdings (ticker, name, h_type, quantity_shares) VALUES (%s, %s, %s, %s)",
                        [holding.ticker, holding.name, holding.h_type, holding.quantity_shares])
            self._empty_holding_cache(holding.ticker)

        return self.get_holdings()

    def add_transaction(self, transaction: Transaction) -> list[Transaction]:
        with self._cursor() as cur:
            cur.execute("INSERT INTO transactions (ticker, quantity, price, trans_date, action_taken) VALUES (%s, %s, %s, %s, %s)",
                        [transaction.ticker, transaction.quantity, transaction.price, str(transaction.trans_date), transaction.action_taken])
            self.empty_cache(key="transactions")

        return self.get_transactions()

    # -------------------- UPDATE --------------------

    def update_holding(self, holding: Holding) -> list[Holding]:
        with self._cursor() as cur:
            cur.execute("UPDATE holdings SET name=%s, h_type=%s, quantity_shares=%s WHERE ticker=%s",
                        [holding.name, holding.h_type, holding.quantity_shares, holding.ticker])
            self._empty_holding_cache(holding.ticker)

        return self.get_holdings()

    def update_transaction(self, transaction: Transaction) -> list[Transaction]:
        with self._cursor() as cur:
            cur.execute("UPDATE transactions SET ticker=%s, quantity=%s, price=%s, trans_date=%s, action_taken=%s  WHERE trans_id=%s",
                        [transaction.ticker, transaction.quantity, transaction.price, transaction.trans_date, transaction.action_taken, transaction.trans_id])
            self.empty_cache(key="transactions")

        return self.get_transactions()

    # -------------------- DELETE --------------------

    def delete_holding(self, holding: Holding) -> list[Holding]:
        with self._cursor() as cur:
            cur.execute("DELETE FROM holdings WHERE ticker = %s",
                        [holding.ticker])
            self._empty_holding_cache(holding.ticker)

        return self.get_holdings()

    def delete_transaction(self, transaction: Transaction) -> list[Transaction]:
        with self._cursor() as cur:
            cur.execute("DELETE FROM transactions WHERE trans_id = %s",
                        [transaction.trans_id])
            self.empty_cache(key="transactions")

        return self.get_transactions()
