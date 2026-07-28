-- ============================================================================
-- Dummy data for local development / demos.  PostgreSQL dialect.
--
-- Run against an existing schema:  psql "$DB_CONNECTION_STRING" -f db/seed_dummy_data.sql
--
-- The four tables below are internally consistent, so the Overview page adds
-- up instead of showing four unrelated sets of numbers:
--
--   * transactions net out to exactly the quantity_shares in holdings
--       (e.g. AAPL: buy 30, buy 20, sell 10  ->  40 shares)
--   * cash works out to exactly 10,000.00, assuming an opening deposit of
--       94,411.75, since  94,411.75 - 92,269.25 (buys) + 7,857.50 (sells) = 10,000.00
--   * the final portfolio_value row equals holdings market value + that cash:
--       94,738.00 + 10,000.00 = 104,738.00
--
-- The cash row itself is set by the UPDATE at the bottom of this script.
--
-- Prices are invented but plausible; the "current" prices used for the final
-- portfolio_value are listed against each holding below so the math is
-- checkable by hand.
-- ============================================================================

-- Re-running this script will fail on duplicate primary keys.  To reset first,
-- uncomment these three lines (this DELETES all existing rows in these tables):
-- DELETE FROM transactions;
-- DELETE FROM portfolio_value;
-- DELETE FROM holdings;

BEGIN;

-- ---------------------------------------------------------------------------
-- holdings -- 10 positions, quantities matching the ledger below
-- ---------------------------------------------------------------------------
-- name is VARCHAR(20), so company names are abbreviated to fit.
-- h_type is VARCHAR(10) and mirrors what yfinance returns for quoteType.
INSERT INTO holdings (ticker, name, h_type, quantity_shares) VALUES
    ('AAPL',  'Apple Inc.',         'EQUITY', 40),   -- @ 214.80 =  8,592.00
    ('MSFT',  'Microsoft Corp.',    'EQUITY', 25),   -- @ 447.20 = 11,180.00
    ('NVDA',  'NVIDIA Corp.',       'EQUITY', 60),   -- @ 162.35 =  9,741.00
    ('AMZN',  'Amazon.com Inc.',    'EQUITY', 30),   -- @ 221.40 =  6,642.00
    ('GOOGL', 'Alphabet Inc.',      'EQUITY', 20),   -- @ 193.60 =  3,872.00
    ('JPM',   'JPMorgan Chase',     'EQUITY', 35),   -- @ 258.90 =  9,061.50
    ('JNJ',   'Johnson & Johnson',  'EQUITY', 45),   -- @ 165.75 =  7,458.75
    ('VOO',   'Vanguard S&P 500',   'ETF',    50),   -- @ 561.30 = 28,065.00
    ('QQQ',   'Invesco QQQ Trust',  'ETF',    15),   -- @ 508.65 =  7,629.75
    ('SCHD',  'Schwab US Dividend', 'ETF',    80);   -- @  31.20 =  2,496.00
                                                     --  market value 94,738.00

-- ---------------------------------------------------------------------------
-- transactions -- 16 rows, chronological, spanning the portfolio_value window
-- ---------------------------------------------------------------------------
-- trans_id is omitted so the SERIAL sequence assigns it; hardcoding ids here
-- would leave the sequence behind and break the next real INSERT.
INSERT INTO transactions (ticker, quantity, price, trans_date, action_taken) VALUES
    ('VOO',   50, 512.7500, '2026-03-16 09:47:00', 'buy'),
    ('AAPL',  30, 180.2500, '2026-03-17 10:12:00', 'buy'),
    ('MSFT',  25, 415.5000, '2026-03-19 14:35:00', 'buy'),
    ('NVDA',  40, 118.7500, '2026-03-24 11:02:00', 'buy'),
    ('AMZN',  30, 198.6000, '2026-04-02 15:20:00', 'buy'),
    ('GOOGL', 25, 172.3000, '2026-04-09 09:55:00', 'buy'),
    ('NVDA',  35, 132.4000, '2026-04-21 13:41:00', 'buy'),
    ('JPM',   35, 242.1500, '2026-04-28 10:30:00', 'buy'),
    ('JNJ',   45, 158.4000, '2026-05-05 11:18:00', 'buy'),
    ('AAPL',  20, 195.1000, '2026-05-12 14:07:00', 'buy'),
    ('QQQ',   20, 468.3000, '2026-05-26 09:38:00', 'buy'),
    ('SCHD',  80,  28.9500, '2026-06-02 15:52:00', 'buy'),
    ('NVDA',  15, 155.8000, '2026-06-16 10:44:00', 'sell'),
    ('AAPL',  10, 210.0000, '2026-07-07 13:26:00', 'sell'),
    ('GOOGL',  5, 188.9000, '2026-07-14 11:09:00', 'sell'),
    ('QQQ',    5, 495.2000, '2026-07-21 14:50:00', 'sell');

-- ---------------------------------------------------------------------------
-- portfolio_value -- 20 weekly points (Mondays), 2026-03-16 .. 2026-07-27
-- ---------------------------------------------------------------------------
-- Starts at the opening deposit (all cash, nothing bought yet) and trends up
-- ~11% with several down weeks, so the line graph has some shape to it.
INSERT INTO portfolio_value (p_date, value) VALUES
    ('2026-03-16',  94411.75),   -- opening deposit, before the first buy settles
    ('2026-03-23',  93780.40),
    ('2026-03-30',  95204.15),
    ('2026-04-06',  94116.80),
    ('2026-04-13',  96530.25),
    ('2026-04-20',  97845.60),
    ('2026-04-27',  96720.35),
    ('2026-05-04',  98410.90),
    ('2026-05-11',  99875.20),
    ('2026-05-18',  98640.55),
    ('2026-05-25', 100320.75),
    ('2026-06-01', 101745.30),
    ('2026-06-08', 100480.65),
    ('2026-06-15', 102910.40),
    ('2026-06-22', 104220.85),
    ('2026-06-29', 103105.50),
    ('2026-07-06', 105640.20),
    ('2026-07-13', 104875.95),
    ('2026-07-20', 106230.70),
    ('2026-07-27', 104738.00);   -- = holdings market value + 10,000.00 cash

-- ---------------------------------------------------------------------------
-- cash -- the single row the portfolio's cash balance lives in
-- ---------------------------------------------------------------------------
-- UPDATE rather than INSERT, since the row is created elsewhere.  Note this is
-- a silent no-op if no row with uid = 'user' exists yet -- UPDATE does not
-- error on zero matches, so check the row count if the balance looks wrong.
UPDATE cash SET value = 10000.00 WHERE uid = 'user';

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification -- uncomment to confirm the ledger still agrees with holdings.
-- Every row should come back with diff = 0.
-- ---------------------------------------------------------------------------
-- SELECT h.ticker,
--        h.quantity_shares AS holdings_qty,
--        COALESCE(SUM(CASE WHEN t.action_taken = 'buy'  THEN  t.quantity
--                          WHEN t.action_taken = 'sell' THEN -t.quantity
--                     END), 0) AS ledger_qty,
--        h.quantity_shares
--            - COALESCE(SUM(CASE WHEN t.action_taken = 'buy'  THEN  t.quantity
--                                WHEN t.action_taken = 'sell' THEN -t.quantity
--                           END), 0) AS diff
--   FROM holdings h
--   LEFT JOIN transactions t ON TRIM(t.ticker) = TRIM(h.ticker)
--  GROUP BY h.ticker, h.quantity_shares
--  ORDER BY h.ticker;