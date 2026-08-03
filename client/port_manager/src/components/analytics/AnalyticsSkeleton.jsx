import React from 'react';
import '../skeleton/Skeleton.css';
import './AnalyticsSkeleton.css';

// Placeholder cards for the first load of the Analytics page. These mirror the
// real cards' structure -- same grid slots, same headers, same row heights -- so
// the page doesn't jump around when the data lands and the components swap in.
//
// Returns the risk card's skeleton plus a right-column wrapper (movers, then
// drawdown, then run-up) rather than one flat list, because the parent
// .analytics-main-content is a two-column grid and these need to be its two
// direct items -- matching exactly what the loaded page renders.

// Matches the dumbbell's default: eight positions plus the cash row.
const DUMBBELL_ROWS = 9;

// Varying the bar widths keeps the block from reading as a table of identical
// grey slabs -- it suggests text of different lengths.
const SYMBOL_WIDTHS = ['62%', '78%', '54%', '70%', '58%', '82%', '66%', '50%', '74%'];

// Where each row's two dots sit along its track. Real rows put money and risk at
// different points, so a placeholder with every pair in the same place would read
// as a grid rather than as a chart.
const DOT_PAIRS = [
  [18, 62], [30, 44], [12, 30], [44, 70], [26, 38],
  [55, 34], [22, 52], [38, 20], [64, 48],
];

export function AnalyticsSkeleton() {
  return (
    <>
      <div className="card risk-card skeleton-card" aria-hidden="true">
        <div className="analytics-skeleton-header">
          <div className="skeleton skeleton-heading" />
        </div>

        <div className="analytics-skeleton-headline">
          <div className="skeleton analytics-skeleton-beta" />
          <div className="skeleton analytics-skeleton-chip" />
        </div>

        <div className="skeleton analytics-skeleton-meter" />
        <div className="analytics-skeleton-scale">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="skeleton skeleton-text analytics-skeleton-scale-label" />
          ))}
        </div>

        <div className="skeleton analytics-skeleton-takeaway" />

        <div className="analytics-skeleton-legend">
          <div className="skeleton skeleton-text analytics-skeleton-legend-item" />
          <div className="skeleton skeleton-text analytics-skeleton-legend-item" />
        </div>

        <div className="analytics-skeleton-rows">
          {Array.from({ length: DUMBBELL_ROWS }, (_, i) => {
            const [money, risk] = DOT_PAIRS[i];
            return (
              <div key={i} className="analytics-skeleton-row">
                {/* the bar varies its width inside a fixed-width cell -- putting
                    the percentage on the flex item itself would measure it
                    against the whole row and push the track off the card */}
                <div className="analytics-skeleton-symbol">
                  <div
                    className="skeleton skeleton-text"
                    style={{ width: SYMBOL_WIDTHS[i] }}
                  />
                </div>
                <div className="analytics-skeleton-track">
                  <div
                    className="skeleton analytics-skeleton-connector"
                    style={{ left: `${Math.min(money, risk)}%`, width: `${Math.abs(risk - money)}%` }}
                  />
                  <div className="skeleton analytics-skeleton-dot" style={{ left: `${money}%` }} />
                  <div className="skeleton analytics-skeleton-dot" style={{ left: `${risk}%` }} />
                </div>
                <div className="skeleton skeleton-text analytics-skeleton-values" />
                <div className="skeleton skeleton-text analytics-skeleton-beta-cell" />
              </div>
            );
          })}
        </div>

        <div className="analytics-skeleton-footnote">
          <div className="skeleton skeleton-text" />
        </div>
      </div>

      <div className="analytics-right-column">
        <div className="card movers-card skeleton-card" aria-hidden="true">
          <div className="skeleton skeleton-heading analytics-skeleton-movers-heading" />
          <div className="skeleton skeleton-text analytics-skeleton-movers-subtitle" />

          {Array.from({ length: 2 }, (_, i) => (
            <div key={i} className="analytics-skeleton-mover-row">
              <div className="skeleton analytics-skeleton-pill" />
              <div className="analytics-skeleton-stack">
                <div className="skeleton skeleton-text analytics-skeleton-mover-symbol" />
                <div className="skeleton skeleton-text analytics-skeleton-mover-name" />
              </div>
              <div className="analytics-skeleton-stack analytics-skeleton-stack-end">
                <div className="skeleton skeleton-text analytics-skeleton-mover-price" />
                <div className="skeleton skeleton-text analytics-skeleton-mover-change" />
              </div>
            </div>
          ))}
        </div>

        {['Max drawdown', 'Max run-up'].map((label) => (
          <div key={label} className="card drawdown-runup-card skeleton-card" aria-hidden="true">
            <div className="skeleton skeleton-heading" />
            <div className="skeleton analytics-skeleton-drawdown-headline" />
            {Array.from({ length: 4 }, (_, i) => (
              <div key={i} className="analytics-skeleton-drawdown-row">
                <div className="skeleton skeleton-text analytics-skeleton-drawdown-label" />
                <div className="skeleton skeleton-text analytics-skeleton-drawdown-value" />
              </div>
            ))}
          </div>
        ))}
      </div>

      <span className="skeleton-sr-only" role="status">Loading analytics…</span>
    </>
  );
}

