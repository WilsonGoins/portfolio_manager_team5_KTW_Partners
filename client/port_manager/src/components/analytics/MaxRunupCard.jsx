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

// data is the "runup" half of the /api/analytics/drawdown response -- null
// when there's not yet enough portfolio history to compute this.
export function MaxRunupCard({ data }) {
  if (!data) {
    return (
      <div className="card drawdown-runup-card">
        <h3>Max run-up</h3>
        <p className="drawdown-runup-empty">Not enough history to calculate this yet.</p>
      </div>
    );
  }

  const { pct, trough_value, trough_date, peak_value, peak_date,
    incline_days, since_peak_pct, at_new_high } = data;

  return (
    <div className="card drawdown-runup-card">
      <h3>Max run-up</h3>
      <div className="drawdown-runup-headline positive">+{pct.toFixed(1)}%</div>

      <div className="drawdown-runup-stats">
        <div className="drawdown-runup-row">
          <span className="drawdown-runup-label">Trough</span>
          <span className="drawdown-runup-value">
            {currency.format(trough_value)} &middot; {formatDate(trough_date)}
          </span>
        </div>
        <div className="drawdown-runup-row">
          <span className="drawdown-runup-label">Peak</span>
          <span className="drawdown-runup-value">
            {currency.format(peak_value)} &middot; {formatDate(peak_date)}
          </span>
        </div>
        <div className="drawdown-runup-row">
          <span className="drawdown-runup-label">Incline</span>
          <span className="drawdown-runup-value">
            {incline_days} day{incline_days === 1 ? '' : 's'}
          </span>
        </div>
        <div className="drawdown-runup-row drawdown-runup-row-last">
          <span className="drawdown-runup-label">Since peak</span>
          {at_new_high ? (
            <span className="drawdown-runup-value positive">At a new high</span>
          ) : (
            <span className="drawdown-runup-value muted">
              Down {Math.abs(since_peak_pct).toFixed(1)}% from peak
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
