import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, Tooltip, YAxis, XAxis } from 'recharts';
import './SecurityCard.css';

export function SecurityCard({ data }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [quantity, setQuantity] = useState(1);
  const [selectedRange, setSelectedRange] = useState('1M');
  const [currentShares, setCurrentShares] = useState(0);
  const [currentAlloc, setCurrentAlloc] = useState(0);
  const [currentMarketValue, setCurrentMarketValue] = useState(0.00);
  const [isLoading, setIsLoading] = useState(true);


 async function fetchHoldingInfo() {
  try {
    setIsLoading(true);
    const response = await fetch('/api/overview'); 

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    const overviewData = await response.json();
    const holdingsData = overviewData?.HoldingsTable || [];

    const holding = holdingsData.find(
      (item) => item.symbol === data.symbol
    );

    setCurrentShares(holding ? holding.num_shares : 0);
    setCurrentAlloc(holding ? Number(holding.allocation_pct).toFixed(2) : '0.00');
    setCurrentMarketValue(holding ? Number(holding.market_value).toFixed(2) : '0.00');
  } catch (err) {
    console.error("Failed to fetch overview data:", err);
  } finally {
    setIsLoading(false);
  }
}
  const {
    symbol,
    name,
    h_type,
    curr_price,
    previous_close,
    pe_ratio = 32.4,
    market_cap = '$3.05T',
    high_52wk = 237.23,
    low_52wk = 164.08,
    volume = '48.2M',
    performanceHistory = {
      '1W': [{ label: 'Mon', p: 195.1 }, { label: 'Wed', p: 194.8 }, { label: 'Fri', p: 198.45 }],
      '1M': [{ label: 'W1', p: 188.2 }, { label: 'W2', p: 191.5 }, { label: 'W3', p: 189.4 }, { label: 'W4', p: 198.45 }],
      '1Y': [{ label: 'Q1', p: 165.0 }, { label: 'Q2', p: 178.5 }, { label: 'Q3', p: 185.2 }, { label: 'Q4', p: 198.45 }],
      'YTD': [{ label: 'Jan', p: 172.1 }, { label: 'Mar', p: 181.0 }, { label: 'May', p: 189.3 }, { label: 'Jul', p: 198.45 }],
    },
  } = data;

  const currentChartData = performanceHistory[selectedRange] || performanceHistory['1M'];
  const priceChange = curr_price - previous_close;
  const percentChange = (priceChange / previous_close) * 100;
  const isPositive = priceChange >= 0;

  const chartColor = isPositive ? '#10b981' : '#ef4444';
  const gradientId = `colorPrice-${symbol}`;

  const handleBuy = (e) => {
    e.stopPropagation();
    console.log(`Buy order: ${quantity} shares of ${symbol}`);
  };

  const handleSell = (e) => {
    e.stopPropagation();
    console.log(`Sell order: ${quantity} shares of ${symbol}`)
  }

  const handleRangeChange = (e, range) => {
    e.stopPropagation();
    setSelectedRange(range);
  };

  return (
    <div
      className={`security-card ${isExpanded ? 'expanded' : ''}`}
      onClick={() => {setIsExpanded(!isExpanded); if (!isExpanded) fetchHoldingInfo() }}
    >
      <div className="card-top-row">
        <div>
          <div className="security-title-group">
            <span className="security-symbol">{symbol}</span>
            <span className="security-type">{h_type}</span>
          </div>
          <p className="security-name">{name}</p>
        </div>

        <div className="price-group">
          <span className="price-label">Current Price</span>
          <div className="price-and-badge">
            <span className="price-value">${curr_price.toFixed(2)}</span>
            <div className={`change-badge ${isPositive ? 'positive' : 'negative'}`}>
              <span>{isPositive ? '▲' : '▼'}</span>
              <span>
                {isPositive ? '+' : ''}
                {priceChange.toFixed(2)} ({percentChange.toFixed(2)}%)
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="graph-section">
        <div className="graph-header">
          <span className="section-label">Performance Trend</span>
          <div className="timeframe-selector">
            {['1W', '1M', '1Y', 'YTD'].map((range) => (
              <button
                key={range}
                type="button"
                className={`timeframe-btn ${selectedRange === range ? 'active' : ''}`}
                onClick={(e) => handleRangeChange(e, range)}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={100}>
            <AreaChart data={currentChartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <YAxis domain={['dataMin - 2', 'dataMax + 2']} hide />
              <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  borderColor: '#334155',
                  borderRadius: '6px',
                  fontSize: '12px',
                  color: '#fff',
                }}
                formatter={(val) => [`$${val.toFixed(2)}`, 'Price']}
              />
              <Area
                type="monotone"
                dataKey="p"
                stroke={chartColor}
                strokeWidth={2}
                fillOpacity={1}
                fill={`url(#${gradientId})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="metrics-row">
        <div className="metric-item">
          <span className="metric-label">P/E Ratio</span>
          <span className="metric-value">{pe_ratio}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Market Cap</span>
          <span className="metric-value">{market_cap}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">52-Wk Range</span>
          <span className="metric-value">
            ${low_52wk} - ${high_52wk}
          </span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Volume</span>
          <span className="metric-value">{volume}</span>
        </div>
      </div>

      <div className="expand-prompt">
        {isExpanded ? 'Click to hide buy options' : 'Click card to buy'}
      </div>

      {isExpanded && (
        <div className="buy-panel-container" onClick={(e) => e.stopPropagation()}>
          <div className="divider" />
            <div className="holding-info">
              <p><b>Personal Holding Information for {symbol}:</b></p>
              {isLoading ? (
                <p>Loading...</p>
              ) : (
                <>
                  <p>Owned Shares: {currentShares}</p>
                  <p>Market Value: ${currentMarketValue ? Number(currentMarketValue).toFixed(2) : 0.00}</p>
                  <p>Allocation: {currentAlloc}%</p>
                </>
              )}
            </div>
          <div className="buy-panel">
            <div className="buy-input-group">
              <label htmlFor={`qty-${symbol}`}>Qty:</label>
              <input
                id={`qty-${symbol}`}
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="buy-quantity-input"
              />
            </div>
            <button className="buy-button" onClick={handleSell} disabled={quantity > currentShares}>
              Sell (${(curr_price * quantity).toFixed(2)})
            </button>
            <button className="buy-button" onClick={handleBuy}>
              Buy (${(curr_price * quantity).toFixed(2)})
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
