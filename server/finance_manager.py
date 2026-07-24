import yfinance
import logging


class FinanceManager:
    """This class is responsible for handling all yahoo finance queries"""

    def __init__(self, flask_logger: logging.Logger):
        self.logger = flask_logger

    # SHOULD INCLUDE ANY METHODS WE WOULD NEED TO POPULATE EXPLORE PAGE
    # - search functionality to return a specific security from name or symbol
    # - a method to return a FEATURED* list of securities to look at on explore landing poge
    # - other stuff that could be useful??
    #
    # Maybe it would make the codebase neater if instead of returning dicts or wtv
    # yfinance returns make our own custom security object resembling db_items.Holding for example
