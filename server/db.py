# ALL CRUD OPERATIONS AND ANYTHING RELATED TO DB GOES HERE
#

class DBManager():
    """Handles all db related needs"""

    def __init__(self, conn_str):
        self.conn_str = conn_str
        # other stuff go here
        #

    def get_holding(self, ticker: str) -> dict:
        raise NotImplementedError

    def get_transaction(self, trans_id: int) -> dict:
        raise NotImplementedError

    def get_holdings(self) -> dict:
        raise NotImplementedError

    # place holders ^^^
