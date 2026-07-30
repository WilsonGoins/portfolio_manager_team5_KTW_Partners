import React from 'react';
import './OverviewSkeleton.css';

// Placeholder cards for the first load of the Overview page. These mirror the real
// cards' structure -- same grid slots, same headers, same row heights -- so the page
// doesn't jump around when the data lands and the components swap in.
//
// Returns four fragments' worth of cards rather than a wrapper div, because the
// parent .overview-main-content is the grid and these need to be its direct items.

// The holdings grid's columns, in the same flex ratios as HoldingsCard's columnDefs.
const HOLDINGS_COLUMNS = [1, 2, 1, 1, 1, 1.2, 1, 1];
const HOLDINGS_ROWS = 6;
const WATCHLIST_ROWS = 5;
const ALLOCATION_ROWS = 4;

// Varying the bar widths keeps the block from reading as a table of identical
// grey slabs -- it suggests text of different lengths.
const CELL_WIDTHS = ['70%', '85%', '55%', '60%', '75%', '65%'];

export function OverviewSkeleton() {
  return (
    <>
      <div className="card portfolio-value-card skeleton-card" aria-hidden="true">
        <div className="skeleton skeleton-heading" />
        <div className="skeleton skeleton-value" />
        <div className="skeleton skeleton-change-pill" />

        <div className="skeleton-timeframes">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="skeleton skeleton-timeframe-button" />
          ))}
        </div>

        <div className="skeleton skeleton-chart" />
      </div>

      <div className="card watchlist-card skeleton-card" aria-hidden="true">
        <div className="skeleton skeleton-heading" />

        <div className="skeleton-list-header">
          <div className="skeleton skeleton-text skeleton-text-sm" style={{ width: '52px' }} />
          <div className="skeleton skeleton-text skeleton-text-sm" style={{ width: '38px' }} />
        </div>

        {Array.from({ length: WATCHLIST_ROWS }, (_, i) => (
          <div key={i} className="skeleton-list-row">
            <div className="skeleton-stack">
              <div className="skeleton skeleton-text" style={{ width: '54px' }} />
              <div className="skeleton skeleton-text skeleton-text-sm" style={{ width: CELL_WIDTHS[i] }} />
            </div>
            <div className="skeleton-stack skeleton-stack-end">
              <div className="skeleton skeleton-text" style={{ width: '62px' }} />
              <div className="skeleton skeleton-text skeleton-text-sm" style={{ width: '46px' }} />
            </div>
          </div>
        ))}
      </div>

      <div className="card holdings-card skeleton-card" aria-hidden="true">
        <div className="skeleton skeleton-heading" />

        <div className="skeleton-grid-row skeleton-grid-header">
          {HOLDINGS_COLUMNS.map((flex, i) => (
            <div key={i} style={{ flex }}>
              <div className="skeleton skeleton-text skeleton-text-sm" style={{ width: '60%' }} />
            </div>
          ))}
        </div>

        {Array.from({ length: HOLDINGS_ROWS }, (_, row) => (
          <div key={row} className="skeleton-grid-row">
            {HOLDINGS_COLUMNS.map((flex, col) => (
              <div key={col} style={{ flex }}>
                <div
                  className="skeleton skeleton-text"
                  style={{ width: CELL_WIDTHS[(row + col) % CELL_WIDTHS.length] }}
                />
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="card allocation-card skeleton-card" aria-hidden="true">
        <div className="skeleton skeleton-heading" />

        {/* matches the real donut's 220px band and 60/90 inner/outer radii */}
        <div className="skeleton-donut-container">
          <div className="skeleton skeleton-donut" />
        </div>

        <div className="skeleton-list-header">
          <div className="skeleton skeleton-text skeleton-text-sm" style={{ width: '36px' }} />
          <div className="skeleton skeleton-text skeleton-text-sm" style={{ width: '42px' }} />
        </div>

        {Array.from({ length: ALLOCATION_ROWS }, (_, i) => (
          <div key={i} className="skeleton-list-row skeleton-list-row-compact">
            <div className="skeleton-identity">
              <div className="skeleton skeleton-legend-icon" />
              <div className="skeleton skeleton-text" style={{ width: CELL_WIDTHS[i] }} />
            </div>
            <div className="skeleton-stack skeleton-stack-end">
              <div className="skeleton skeleton-text" style={{ width: '76px' }} />
            </div>
          </div>
        ))}
      </div>

      <span className="skeleton-sr-only" role="status">Loading portfolio data…</span>
    </>
  );
}
