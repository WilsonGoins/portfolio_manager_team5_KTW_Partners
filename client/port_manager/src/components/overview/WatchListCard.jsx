import React from 'react';
import './WatchListCard.css';
import { useNavigate } from 'react-router-dom';

export function WatchListCard({ data }) {
  const movers = data ?? [];
  const navigate = useNavigate();


  const handleRowClick = (symbol) => {
      navigate(`/details/${symbol}`);
  };

  return (
    <div className="card watchlist-card">
      <h3>Watchlist</h3>
      {movers.length === 0 ? (
        <p className="watchlist-empty-message">No movers available right now.</p>
      ) : (
        <div className="watchlist-list">
          <div className="watchlist-header">
            <span>Symbol</span>
            <span>Price</span>
          </div>

          {movers.map((stock) => (
            <div key={stock.symbol} className="watchlist-item" onClick={() => {handleRowClick(stock.symbol)}}>
              <div className="stock-identity">
                <span className="stock-symbol">{stock.symbol}</span>
                <span className="stock-name" title={stock.name}>{stock.name}</span>
              </div>
              <div className="stock-prices">
                <span className="stock-price">${stock.price.toFixed(2)}</span>
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
