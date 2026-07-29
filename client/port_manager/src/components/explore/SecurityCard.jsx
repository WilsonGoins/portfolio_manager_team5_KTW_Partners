import React from 'react';
import './SecurityCard.css';

export function SecurityCard({ data }) {
  const { symbol, name, h_type, curr_price, previous_close } = data;

  const priceChange = curr_price - previous_close;
  const percentChange = (priceChange / previous_close) * 100;
  const isPositive = priceChange >= 0;

  return (
    <div className="security-card">
      <div>
        <div className="security-card-header">
          <span className="security-symbol">{symbol}</span>
          <span className="security-type">{h_type}</span>
        </div>
        <p className="security-name">{name}</p>
      </div>

      <div className="security-card-body">
        <div>
          <span className="price-label">Current Price</span>
          <span className="price-value">${curr_price.toFixed(2)}</span>
        </div>

        <div className={`change-badge ${isPositive ? 'positive' : 'negative'}`}>
          <span>{isPositive ? '▲' : '▼'}</span>
          <span>
            {isPositive ? '+' : ''}
            {priceChange.toFixed(2)} ({percentChange.toFixed(2)}%)
          </span>
        </div>
      </div>
    </div>
  );
}
