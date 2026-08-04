import logging
from contextlib import contextmanager
from typing import Any, Iterator
from db_items import Holding, Transaction, PortfolioValue
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from psycopg import Cursor
from datetime import datetime

_CASH_PK = "user"


class DBManager:
    """Manages database connections, transactions, and caching for portfolio operations.

    Provides high-level CRUD operations for portfolio values, holdings, transactions,
    and cash balances utilizing PostgreSQL connection pooling (`psycopg_pool`) and an
    in-memory dictionary cache.

    Args:
        conn_str (str): PostgreSQL connection string.
        flask_logger (logging.Logger): Logger instance for operational logging.
        enable_cache (bool, optional): Toggles in-memory query result caching.
            Defaults to True.
    """

    def __init__(
        self, conn_str: str, flask_logger: logging.Logger, enable_cache: bool = True
    ):
        """Initializes the database manager and connection pool."""
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
            open=False,
        )

        try:
            self._pool.open(wait=True, timeout=10)
            self.logger.info("Database connected successfully.")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {
                              e}", exc_info=True)
            self.logger.error("WE SHOULD RERAISE HERE TO BE HANDLED IN API CONTROLLER")

    @contextmanager
    def _cursor(self) -> Iterator[Cursor]:
        """Context manager to check out a pooled database connection and yield a cursor.

        Automatically commits transactions upon normal exit or rolls back in case
        of an exception, ensuring connections do not remain idle in transaction.

        Yields:
            Cursor: A psycopg database cursor configured with `dict_row` factory.
        """
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                yield cur

    def empty_cache(self, key: str | None = None) -> None:
        """Clears specific key or all entries from the in-memory cache.

        Args:
            key (str | None, optional): The specific cache key to purge.
                If None, flushes the entire cache dictionary. Defaults to None.
        """
        if key is None:
            self._cache = {}
            self._enable_cache and self.logger.debug("Cache[DELETE] Cleared all keys.")
        else:
            self._cache.pop(key, None)
            self._enable_cache and self.logger.debug(
                f"Cache[DELETE] Cleared cache for key: {key}"
            )

    def _empty_holding_cache(self, ticker_symbol: str) -> None:
        """Invalidates both individual and collection holdings cache entries.

        Ensures data consistency across single holding queries and full-list reads
        when a holding is added, modified, or removed.

        Args:
            ticker_symbol (str): The ticker symbol of the holding cache to invalidate.
        """
        self.empty_cache(key="holdings")
        self.empty_cache(key=f"holding:{ticker_symbol}")

    # -------------------- CASH --------------------

    def get_cash(self) -> float | None:
        """Retrieves the current cash balance for the default user.

        Returns:
            float | None: Current cash balance if recorded, or None if no balance exists.
        """
        with self._cursor() as cur:
            cur.execute("SELECT value FROM cash WHERE uid = %s", [_CASH_PK])
            cash_row = cur.fetchone()
            cash_value: float = (
                float(cash_row["value"]) if cash_row is not None else None
            )

            return cash_value

    def set_cash(self, new_value: float) -> float:
        """Updates or inserts the cash balance for the default user.

        Args:
            new_value (float): The new cash balance amount to set.

        Returns:
            float: The newly assigned cash balance.
        """
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

    def get_portfolio_value(self, p_date: datetime) -> PortfolioValue | None:
        """Fetches the recorded portfolio value for a specific target date.

        Args:
            p_date (datetime): The timestamp date to query.

        Returns:
            PortfolioValue | None: The portfolio value instance if present, else None.
        """
        if self._enable_cache and f"pv:{p_date}" in self._cache:
            self.logger.debug(f'Cache[HIT] "pv:{p_date}": {
                              self._cache[f"pv:{p_date}"]}')
            return self._cache[f"pv:{p_date}"]
        else:
            self.logger.debug(f'Cache[MISS] "pv:{p_date}"')

        with self._cursor() as cur:
            cur.execute("SELECT * FROM portfolio_value WHERE p_date = %s", [p_date])

            pv_dict = cur.fetchone()
            if pv_dict is None:
                return None

            pv = PortfolioValue.from_dict(pv_dict)
            if self._enable_cache:
                self._cache[f"pv:{p_date}"] = pv
                self.logger.debug(f'CACHE[UPDATE] "pv:{
                    p_date}": {pv}')

            return pv

    def get_portfolio_values(self) -> list[PortfolioValue]:
        """Retrieves historical portfolio values ordered by date descending.

        Returns:
            list[PortfolioValue]: List of historical portfolio value objects.
        """
        if self._enable_cache and "portfolio_values" in self._cache:
            self.logger.debug(f'Cache[HIT] "portfolio_values": {
                              self._cache["portfolio_values"]}')
            return self._cache["portfolio_values"]
        else:
            self.logger.debug('Cache[MISS] "portfolio_values"')

        with self._cursor() as cur:
            cur.execute(
                "SELECT p_date, value as total_value, day_change, day_change_pct FROM portfolio_value ORDER BY p_date DESC"
            )

            portfolio_values: list[PortfolioValue] = []
            for pv_dict in cur.fetchall():
                portfolio_values.append(PortfolioValue.from_dict(pv_dict))

            if self._enable_cache:
                self._cache["portfolio_values"] = portfolio_values
                self.logger.debug(f'CACHE[UPDATE] "portfolio_values": {
                                  portfolio_values}')

            return portfolio_values

    def get_holding(self, ticker_symbol: str) -> Holding | None:
        """Fetches current position details for a specific ticker symbol.

        Args:
            ticker_symbol (str): Ticker symbol to query (e.g., "AAPL").

        Returns:
            Holding | None: Holding object if held in portfolio, else None.
        """
        if self._enable_cache and f"holding:{ticker_symbol}" in self._cache:
            self.logger.debug(f'Cache[HIT] "holding:{ticker_symbol}": {
                              self._cache[ticker_symbol]}')
            return self._cache[f"holding:{ticker_symbol}"]
        else:
            self.logger.debug(f'Cache[MISS] "holding:{ticker_symbol}"')

        with self._cursor() as cur:
            cur.execute("SELECT * FROM holdings WHERE ticker = %s", [ticker_symbol])

            holding_dict = cur.fetchone()
            if holding_dict is None:
                return None

            holding = Holding.from_dict(holding_dict)
            if self._enable_cache:
                self._cache[f"holding:{ticker_symbol}"] = holding
                self.logger.debug(f'CACHE[UPDATE] "holding:{
                    ticker_symbol}": {holding}')

            return holding

    def get_holdings(self) -> list[Holding]:
        """Retrieves all current portfolio holdings.

        Returns:
            list[Holding]: List of current portfolio holdings objects.
        """
        if self._enable_cache and "holdings" in self._cache:
            self.logger.debug(f'Cache[HIT] "holdings": {
                              self._cache["holdings"]}')
            return self._cache["holdings"]
        else:
            self.logger.debug('Cache[MISS] "holdings"')

        with self._cursor() as cur:
            cur.execute("SELECT * FROM holdings")

            holdings: list[Holding] = []
            for holding_dict in cur.fetchall():
                holdings.append(Holding.from_dict(holding_dict))

            if self._enable_cache:
                self._cache["holdings"] = holdings
                self.logger.debug(f'CACHE[UPDATE] "holdings": {holdings}')

            return holdings

    def get_transaction(self, trans_id: int) -> Transaction | None:
        """Retrieves a single transaction record by its primary key ID.

        Args:
            trans_id (int): Database transaction ID.

        Returns:
            Transaction | None: Transaction instance if found, else None.
        """
        # TODO: delete this? how would we even query b the transaction id? they are set by the db and random
        if self._enable_cache and f"transaction:{trans_id}" in self._cache:
            self.logger.debug(f'Cache[HIT] "transaction:{trans_id}": {
                              self._cache[trans_id]}')
            return self._cache[f"transaction:{trans_id}"]
        else:
            self.logger.debug(f'Cache[MISS] "transaction:{trans_id}"')

        with self._cursor() as cur:
            cur.execute("SELECT * FROM transactions WHERE trans_id = %s", [trans_id])

            transaction_dict = cur.fetchone()
            if transaction_dict is None:
                return None

            transaction = Transaction.from_dict(transaction_dict)
            if self._enable_cache:
                self._cache[f"transaction:{trans_id}"] = transaction
                self.logger.debug(f'CACHE[UPDATE] "transaction:{
                    trans_id}": {transaction}')

            return transaction

    def get_transactions(self) -> list[Transaction]:
        """Retrieves all historical portfolio transaction records.

        Returns:
            list[Transaction]: List of transaction objects.
        """
        if self._enable_cache and "transactions" in self._cache:
            self.logger.debug(f'Cache[HIT] "transactions": {
                              self._cache["transactions"]}')
            return self._cache["transactions"]
        else:
            self.logger.debug('Cache[MISS] "transactions"')

        with self._cursor() as cur:
            cur.execute("SELECT * FROM transactions")

            transactions: list[Transaction] = []
            for transaction_dict in cur.fetchall():
                transactions.append(Transaction.from_dict(transaction_dict))

            if self._enable_cache:
                self._cache["transactions"] = transactions
                self.logger.debug(f'CACHE[UPDATE] "transactions": {transactions}')
            return transactions

    # -------------------- CREATE --------------------

    def add_portfolio_value(
        self, date: datetime, new_value: float, change: float, change_pct: float
    ) -> list[PortfolioValue]:
        """Inserts a new portfolio valuation snapshot and clears history cache.

        Args:
            date (datetime): Valuation date.
            new_value (float): Total portfolio value.
            change (float): Absolute daily change in value.
            change_pct (float): Percentage daily change in value.

        Returns:
            list[PortfolioValue]: Updated list of all historical portfolio values.
        """
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO portfolio_value (p_date, value, day_change, day_change_pct) VALUES (%s, %s, %s, %s)",
                [date, new_value, change, change_pct],
            )
            self.empty_cache("portfolio_values")

        return self.get_portfolio_values()

    def add_holding(self, holding: Holding) -> list[Holding]:
        """Inserts a new holding position and invalidates relevant caches.

        Args:
            holding (Holding): Holding instance containing position details.

        Returns:
            list[Holding]: Updated list of all current holdings.
        """
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO holdings (ticker, name, h_type, quantity_shares) VALUES (%s, %s, %s, %s)",
                [holding.ticker, holding.name, holding.h_type, holding.quantity_shares],
            )
            self._empty_holding_cache(holding.ticker)

        return self.get_holdings()

    def add_transaction(self, transaction: Transaction) -> list[Transaction]:
        """Records a new buy/sell transaction and invalidates the transactions cache.

        Args:
            transaction (Transaction): Transaction instance containing trade metadata.

        Returns:
            list[Transaction]: Updated list of all transaction records.
        """
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO transactions (ticker, quantity, price, trans_date, action_taken) VALUES (%s, %s, %s, %s, %s)",
                [
                    transaction.ticker,
                    transaction.quantity,
                    transaction.price,
                    str(transaction.trans_date),
                    transaction.action_taken,
                ],
            )
            self.empty_cache(key="transactions")

        return self.get_transactions()

    # -------------------- UPDATE --------------------

    def update_holding(self, holding: Holding) -> list[Holding]:
        """Updates an existing holding position and invalidates relevant caches.

        Args:
            holding (Holding): Holding object containing updated values.

        Returns:
            list[Holding]: Updated list of all current holdings.
        """
        with self._cursor() as cur:
            cur.execute(
                "UPDATE holdings SET name=%s, h_type=%s, quantity_shares=%s WHERE ticker=%s",
                [holding.name, holding.h_type, holding.quantity_shares, holding.ticker],
            )
            self._empty_holding_cache(holding.ticker)

        return self.get_holdings()

    def update_transaction(self, transaction: Transaction) -> list[Transaction]:
        """Updates an existing transaction record and clears the transactions cache.

        Args:
            transaction (Transaction): Transaction object containing modified fields.

        Returns:
            list[Transaction]: Updated list of all transaction records.
        """
        with self._cursor() as cur:
            cur.execute(
                "UPDATE transactions SET ticker=%s, quantity=%s, price=%s, trans_date=%s, action_taken=%s  WHERE trans_id=%s",
                [
                    transaction.ticker,
                    transaction.quantity,
                    transaction.price,
                    transaction.trans_date,
                    transaction.action_taken,
                    transaction.trans_id,
                ],
            )
            self.empty_cache(key="transactions")

        return self.get_transactions()

    # -------------------- DELETE --------------------

    def delete_holding(self, holding: Holding) -> list[Holding]:
        """Deletes a specified position holding and purges associated caches.

        Args:
            holding (Holding): Holding object to remove.

        Returns:
            list[Holding]: Updated list of remaining current holdings.
        """
        with self._cursor() as cur:
            cur.execute("DELETE FROM holdings WHERE ticker = %s", [holding.ticker])
            self._empty_holding_cache(holding.ticker)

        return self.get_holdings()

    def delete_transaction(self, transaction: Transaction) -> list[Transaction]:
        """Deletes a transaction record by its ID and invalidates cache.

        Args:
            transaction (Transaction): Transaction instance to delete.

        Returns:
            list[Transaction]: Updated list of remaining transactions.
        """
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM transactions WHERE trans_id = %s", [transaction.trans_id]
            )
            self.empty_cache(key="transactions")

        return self.get_transactions()
