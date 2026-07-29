import React from 'react';
import './WatchListCard.css';

export function WatchListCard({ data }) {
  const movers = data ?? [];

  return (
    <div className="card watchlist-card">
      <h3>Watchlist</h3>
      {movers.length === 0 ? (
        <p className="watchlist-empty-message">No movers available right now.</p>
      ) : (
        <div className="watchlist-list">
          {movers.map((stock) => (
            <div key={stock.symbol} className="watchlist-item" title={stock.name}>
              <span className="stock-symbol">{stock.symbol}</span>
              <div className="stock-prices">
                  <span className="stock-price">{stock.price.toFixed(2)}</span>
                  <span className={`stock-change ${stock.change >= 0 ? 'positive' : 'negative'}`}>
                      {stock.change >= 0 ? `+${stock.change.toFixed(2)}%` : `${stock.change.toFixed(2)}%`}
                  </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
