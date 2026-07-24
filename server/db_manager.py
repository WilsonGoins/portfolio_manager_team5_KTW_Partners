import psycopg
import logging
from typing import Any
from db_items import Holding, Transaction
from psycopg.rows import dict_row


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
        self._conn = None

        try:
            self._conn = psycopg.connect(conn_str, row_factory=dict_row)
            self.logger.info("Database connected successfully.")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {
                              e}", exc_info=True)
            self.logger.error(
                "WE SHOULD RERAISE HERE TO BE HANDLED IN API CONTROLLER")

    def empty_cache(self):
        self._cache = {}

    # -------------------- READ --------------------

    def get_holding(self, ticker_symbol: str) -> Holding | None:
        if self._enable_cache and f"holding:{ticker_symbol}" in self._cache:
            self.logger.debug(f"Cache[HIT] \"holding:{ticker_symbol}\": {
                              self._cache[ticker_symbol]}")
            return self._cache[f"holding:{ticker_symbol}"]
        else:
            self.logger.debug(f"Cache[MISS] \"holding:{ticker_symbol}\"")

        with self._conn.cursor() as cur:
            cur.execute("SELECT * FROM holdings WHERE id = %s",
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

        with self._conn.cursor() as cur:
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
        if self._enable_cache and f"transaction:{trans_id}" in self._cache:
            self.logger.debug(f"Cache[HIT] \"transaction:{trans_id}\": {
                              self._cache[trans_id]}")
            return self._cache[f"transaction:{trans_id}"]
        else:
            self.logger.debug(f"Cache[MISS] \"transaction:{trans_id}\"")

        with self._conn.cursor() as cur:
            cur.execute("SELECT * FROM transactions WHERE id = %s",
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

        with self._conn.cursor() as cur:
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
        raise NotImplementedError

    def add_transaction(self, transaction: Transaction) -> list[Transaction]:
        raise NotImplementedError

    # -------------------- UPDATE --------------------

    def update_holding(self, holding: Holding) -> Holding:
        raise NotImplementedError

    def update_transaction(self, transaction: Transaction) -> Transaction:
        raise NotImplementedError

    # -------------------- DELETE --------------------

    def delete_holding(self, ticker_symbol: str) -> list[Holding]:
        raise NotImplementedError

    def delete_transaction(self, trans_id: int) -> list[Transaction]:
        raise NotImplementedError
