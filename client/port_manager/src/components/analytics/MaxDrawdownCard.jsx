import React from 'react';
import './DrawdownRunupCard.css';

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const shortDate = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
});

const formatDate = (dateStr) => shortDate.format(new Date(`${dateStr}T00:00:00Z`));

// data is the "drawdown" half of the /api/analytics/drawdown response --
// null when there's not yet enough portfolio history to compute this.
export function MaxDrawdownCard({ data }) {
  if (!data) {
    return (
      <div className="card drawdown-runup-card">
        <h3>Max drawdown</h3>
        <p className="drawdown-runup-empty">Not enough history to calculate this yet.</p>
      </div>
    );
  }

  const { pct, peak_value, peak_date, trough_value, trough_date,
    decline_days, recovered_date, recovery_days } = data;

  return (
    <div className="card drawdown-runup-card">
      <h3>Max drawdown</h3>
      <div className="drawdown-runup-headline negative">{pct.toFixed(1)}%</div>

      <div className="drawdown-runup-stats">
        <div className="drawdown-runup-row">
          <span className="drawdown-runup-label">Peak</span>
          <span className="drawdown-runup-value">
            {currency.format(peak_value)} &middot; {formatDate(peak_date)}
          </span>
        </div>
        <div className="drawdown-runup-row">
          <span className="drawdown-runup-label">Trough</span>
          <span className="drawdown-runup-value">
            {currency.format(trough_value)} &middot; {formatDate(trough_date)}
          </span>
        </div>
        <div className="drawdown-runup-row">
          <span className="drawdown-runup-label">Decline</span>
          <span className="drawdown-runup-value">
            {decline_days} day{decline_days === 1 ? '' : 's'}
          </span>
        </div>
        <div className="drawdown-runup-row drawdown-runup-row-last">
          <span className="drawdown-runup-label">Recovered</span>
          {recovered_date ? (
            <span className="drawdown-runup-value positive">
              {formatDate(recovered_date)} &middot; {recovery_days} day{recovery_days === 1 ? '' : 's'}
            </span>
          ) : (
            <span className="drawdown-runup-value muted">Not yet recovered</span>
          )}
        </div>
      </div>
    </div>
  );
}
