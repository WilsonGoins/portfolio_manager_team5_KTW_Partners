import React from 'react';
import '../skeleton/Skeleton.css';
import './TransactionsSkeleton.css';

// Placeholder for the first load of the Transactions page. Mirrors
// TransactionsTable's grid -- same header and row heights, same column flex
// ratios -- so the table doesn't resize under the reader when the rows land.

// TransactionsTable's columnDefs, in order: Date, Symbol, Action, Shares,
// Price, Total. Kept in step with the flex values there so the placeholder
// columns line up with the real ones.
const COLUMNS = [1.4, 1, 1, 1, 1, 1.2];

// Enough to fill the card without pretending to know how many transactions
// there are. The real grid paginates at 20; this is a screenful.
const ROWS = 8;

// Varying widths keep the block from reading as a table of identical grey slabs.
const CELL_WIDTHS = ['78%', '55%', '64%', '48%', '70%', '60%'];

export function TransactionsSkeleton() {
  return (
    <div className="card transactions-card skeleton-card" aria-hidden="true">
      <div className="skeleton transactions-skeleton-heading" />

      <div className="transactions-skeleton-grid">
        <div className="transactions-skeleton-row transactions-skeleton-header">
          {COLUMNS.map((flex, i) => (
            <div key={i} className="transactions-skeleton-cell" style={{ flex }}>
              <div className="skeleton skeleton-text transactions-skeleton-header-bar" />
            </div>
          ))}
        </div>

        {Array.from({ length: ROWS }, (_, row) => (
          <div key={row} className="transactions-skeleton-row">
            {COLUMNS.map((flex, col) => (
              <div key={col} className="transactions-skeleton-cell" style={{ flex }}>
                <div
                  className="skeleton skeleton-text"
                  style={{ width: CELL_WIDTHS[(row + col) % CELL_WIDTHS.length] }}
                />
              </div>
            ))}
          </div>
        ))}
      </div>

      <span className="skeleton-sr-only" role="status">Loading transactions…</span>
    </div>
  );
}
