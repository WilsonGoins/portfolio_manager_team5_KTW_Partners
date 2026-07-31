import React from 'react';
import './BiggestMoversCard.css';

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// One row of the card: the label pill ("Gainer"/"Loser"), the holding's
// symbol/name, and its price + percent move. `mover` is null when there's
// nothing to show yet (e.g. an empty portfolio), in which case the row falls
// back to a muted placeholder instead of throwing on missing fields.
function MoverRow({ type, mover }) {
  const isGainer = type === 'gainer';
  const label = isGainer ? 'Gainer' : 'Loser';

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
              {mover.change_pct_since_close >= 0 ? '+' : ''}
              {mover.change_pct_since_close.toFixed(2)}%
            </span>
          </div>
        </>
      )}
    </div>
  );
}

// data is the raw {biggest_gainer, biggest_loser} response from
// /api/analytics/movers -- each side is null when nothing qualifies
// (e.g. no holdings, or a quote missing enough data to price).
export function BiggestMoversCard({ data }) {
  const biggestGainer = data?.biggest_gainer ?? null;
  const biggestLoser = data?.biggest_loser ?? null;

  return (
    <div className="card movers-card">
      <h3>Biggest Movers</h3>
      {!biggestGainer && !biggestLoser ? (
        <p className="movers-empty-message">No movers available right now.</p>
      ) : (
        <div className="movers-list">
          <MoverRow type="gainer" mover={biggestGainer} />
          <MoverRow type="loser" mover={biggestLoser} />
        </div>
      )}
    </div>
  );
}
