import React from 'react';
import './BiggestMoversCard.css';

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// One row of the card: the label pill ("Gainer"/"Loser"), the holding's
// symbol/name, and its price + percent gain/loss since it was purchased.
// `mover` is null when there's nothing to show yet (e.g. an empty portfolio,
// or no holding has a computable cost basis), in which case the row falls
// back to a muted placeholder instead of throwing on missing fields.
function MoverRow({ type, mover }) {
  const isGainer = type === 'gainer';
  const label = isGainer ? 'Top Performer' : 'Weakest Performer';

  return (
    <div className={`mover-row mover-row-${type}`}>
      <span className={`mover-pill mover-pill-${type}`}>{label}</span>

      {!mover ? (
        <span className="mover-empty">No data available</span>
      ) : (
        <>
          <div className="mover-identity">
            <span className="mover-symbol">{mover.symbol}</span>
            <span className="mover-name" title={mover.name}>{mover.name}</span>
          </div>
          <div className="mover-prices">
            <span className="mover-price">{currency.format(mover.curr_price)}</span>
            <span className="mover-change">
              {mover.gain_pct_since_purchase >= 0 ? '+' : ''}
              {mover.gain_pct_since_purchase.toFixed(2)}%
            </span>
          </div>
        </>
      )}
    </div>
  );
}

// data is the raw response from /api/analytics/movers -- biggest_gainer and
// biggest_loser are null when nothing qualifies (e.g. no holdings, or no
// holding has a computable cost basis). Gain/loss here is relative to what
// was actually paid for the position, not today's market move -- a stock
// bought today because it was already down doesn't show up as a "loser"
// just for being purchased at a low price.
export function BiggestMoversCard({ data }) {
  const biggestGainer = data?.biggest_gainer ?? null;
  const biggestLoser = data?.biggest_loser ?? null;
  const qualifyingCount = data?.qualifying_count ?? 0;
  const totalPositions = data?.total_positions ?? 0;

  // Only one holding has a computable gain/loss: showing it as both a
  // "Gainer" card and a "Loser" card reads as a duplicate/bug, even though
  // it's technically correct (it's simultaneously the best and worst
  // performer, being the only one). Say that plainly instead, once.
  const onlyOneQualifies = qualifyingCount === 1 && biggestGainer &&
    biggestGainer.symbol === biggestLoser?.symbol;

  return (
    <div className="card movers-card">
      <h3>Biggest Movers</h3>
      <p className="movers-subtitle">Gain/loss vs. your purchase price</p>

      {!biggestGainer && !biggestLoser ? (
        <p className="movers-empty-message">
          {totalPositions > 0
            ? 'No holdings have enough purchase history to calculate this yet.'
            : 'No movers available right now.'}
        </p>
      ) : onlyOneQualifies ? (
        <>
          <p className="movers-single-message">
            Only {biggestGainer.symbol} has enough purchase history to calculate gain/loss right now.
          </p>
          <div className="movers-list">
            <MoverRow type={biggestGainer.gain_pct_since_purchase >= 0 ? 'gainer' : 'loser'} mover={biggestGainer} />
          </div>
        </>
      ) : (
        <div className="movers-list">
          <MoverRow type="gainer" mover={biggestGainer} />
          <MoverRow type="loser" mover={biggestLoser} />
        </div>
      )}
    </div>
  );
}
