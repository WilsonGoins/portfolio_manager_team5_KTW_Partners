import React, { useState, useEffect, useCallback } from 'react';
import { DetailsSkeleton } from '../components/details/DetailsSkeleton'
import { useParams, useNavigate } from 'react-router-dom';
import { ResponsiveContainer, AreaChart, Area, Tooltip, YAxis, XAxis } from 'recharts';
import { formatHoldingType } from '../utils/holdingType';
import './Details.css';

// Yahoo's descriptions run from a couple of sentences to a couple of thousand
// characters, so only the ones that overflow the clamp get a toggle -- roughly
// where the four collapsed lines run out.
const ABOUT_CLAMP_CHARS = 320;

export function Details() {
  const { symbol } = useParams();
  const navigate = useNavigate();

  const [securityData, setSecurityData] = useState(null);
  const [holdingData, setHoldingData] = useState(null);
  const [selectedRange, setSelectedRange] = useState('1M');
  const [tradeMode, setTradeMode] = useState('BUY');
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [aboutExpanded, setAboutExpanded] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setAboutExpanded(false);   // a new security starts collapsed

      const [secRes, overviewRes] = await Promise.all([
        fetch(`/api/search?q=${symbol}`),
        fetch('/api/overview')
      ]);

      if (!secRes.ok) throw new Error(`Failed to fetch security details (${secRes.status})`);

      const secJson = await secRes.json();
      setSecurityData(secJson[0]);

      if (overviewRes.ok) {
        const overviewJson = await overviewRes.json();
        const holdings = overviewJson?.HoldingsTable || [];
        const userHolding = holdings.find((h) => h.symbol === symbol);
        setHoldingData(userHolding || null);
      }

      setError(null);
    } catch (err) {
      console.error('Error fetching details:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExecuteTrade = async (e) => {
    e.preventDefault();
    if (!securityData || quantity <= 0) return;

    setIsSubmitting(true);
    const endpoint = tradeMode === 'BUY' ? '/api/buy' : '/api/sell';

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: symbol,
          quantity: Number(quantity),
        }),
      });

      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Transaction failed');

      await fetchData();
    } catch (err) {
      alert(`Trade Error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <DetailsSkeleton />;
  if (error || !securityData) return <div className="details-error">Error: {error || 'Security not found'}</div>;

  const {
    name,
    h_type,
    curr_price,
    previous_close,
    pe_ratio,
    market_cap,
    high_52wk,
    low_52wk,
    volume,
    description,
    performanceHistory = {},
  } = securityData;

  const priceChange = curr_price - previous_close;
  const percentChange = (priceChange / previous_close) * 100;
  const isPositive = priceChange >= 0;
  const chartColor = isPositive ? '#10b981' : '#ef4444';

  const isAboutLong = Boolean(description) && description.length > ABOUT_CLAMP_CHARS;

  const chartData = performanceHistory[selectedRange] || performanceHistory['1M'] || [];
  const estCost = (curr_price * quantity).toFixed(2);
  const ownedShares = holdingData?.num_shares || 0;

  return (
    <div className="details-container">
      <button className="back-btn" onClick={() => navigate(-1)}>
        &larr; Back
      </button>

      <div className="details-grid">
        <div className="main-panel">
          <div className="card chart-card">
            <div className="chart-header">
              <div>
                <div className="title-row">
                  <h1 className="symbol">{symbol}</h1>
                  <span className="type-badge">{formatHoldingType(h_type)}</span>
                </div>
                <p className="company-name">{name}</p>
                <div className="price-row">
                  <span className="current-price">${curr_price.toFixed(2)}</span>
                  <span className={`price-badge ${isPositive ? 'pos' : 'neg'}`}>
                    {isPositive ? '▲' : '▼'} {priceChange.toFixed(2)} ({percentChange.toFixed(2)}%)
                  </span>
                </div>
              </div>

              <div className="timeframe-buttons">
                {['1W', '1M', '1Y', 'YTD'].map((range) => (
                  <button
                    key={range}
                    className={`tf-btn ${selectedRange === range ? 'active' : ''}`}
                    onClick={() => setSelectedRange(range)}
                  >
                    {range}
                  </button>
                ))}
              </div>
            </div>

            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="lightGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={chartColor} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={chartColor} stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <YAxis domain={['dataMin - 2', 'dataMax + 2']} hide />
                  <XAxis
                    dataKey="label"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    interval="preserveStartEnd"
                    minTickGap={30}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      borderColor: '#e2e8f0',
                      borderRadius: '8px',
                      fontSize: '13px',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                    }}
                    formatter={(val) => [`$${val.toFixed(2)}`, 'Price']}
                  />
                  <Area
                    type="monotone"
                    dataKey="p"
                    stroke={chartColor}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#lightGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card stats-card">
            <h3>KEY STATS</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-label">Market Cap</span>
                <span className="stat-value">{market_cap}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">P/E Ratio</span>
                <span className="stat-value">{pe_ratio}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">52-Week Range</span>
                <span className="stat-value">${low_52wk} - ${high_52wk}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Volume</span>
                <span className="stat-value">{volume}</span>
              </div>
            </div>
          </div>

          {/* Always rendered: Yahoo returns no description often enough that
              saying so beats the card silently vanishing from the page. */}
          <div className="card about-card">
            <h3>ABOUT {symbol}</h3>
            {description ? (
              <>
                <p className={`about-text${isAboutLong && !aboutExpanded ? ' collapsed' : ''}`}>
                  {description}
                </p>
                {isAboutLong && (
                  <button
                    type="button"
                    className="about-toggle"
                    onClick={() => setAboutExpanded((expanded) => !expanded)}
                  >
                    {aboutExpanded ? 'Click to show less.' : 'Click to read more.'}
                  </button>
                )}
              </>
            ) : (
              <p className="about-empty">
                A description is not available for this security.
              </p>
            )}
          </div>
        </div>

        <div className="side-panel">
          <div className="card position-card">
            <h3>YOUR POSITION</h3>
            <div className="position-details">
              <div className="pos-row">
                <span>Shares</span>
                <span>{ownedShares}</span>
              </div>
              <div className="pos-row">
                <span>Market Value</span>
                <span>${holdingData ? Number(holdingData.market_value).toFixed(2) : '0.00'}</span>
              </div>
              <div className="pos-row">
                <span>Portfolio Allocation</span>
                <span>{holdingData ? Number(holdingData.allocation_pct).toFixed(2) : '0.00'}%</span>
              </div>
            </div>
          </div>

          <div className="card trade-card">
            <h3>TRADE {symbol}</h3>

            <div className="trade-toggle">
              <button
                className={`toggle-btn ${tradeMode === 'BUY' ? 'active buy' : ''}`}
                onClick={() => setTradeMode('BUY')}
              >
                Buy
              </button>
              <button
                className={`toggle-btn ${tradeMode === 'SELL' ? 'active sell' : ''}`}
                onClick={() => setTradeMode('SELL')}
              >
                Sell
              </button>
            </div>

            <form onSubmit={handleExecuteTrade} className="trade-form">
              <div className="form-group">
                <label htmlFor="quantity">Quantity</label>
                <input
                  id="quantity"
                  type="number"
                  min="1"
                  max={tradeMode === 'SELL' ? ownedShares : undefined}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  className="qty-input"
                />
              </div>

              <div className="cost-row">
                <span>Est. {tradeMode === 'BUY' ? 'Cost' : 'Credit'}</span>
                <span className="cost-val">${estCost}</span>
              </div>

              <button
                type="submit"
                className={`execute-btn ${tradeMode === 'BUY' ? 'buy' : 'sell'}`}
                disabled={isSubmitting || (tradeMode === 'SELL' && (ownedShares === 0 || quantity > ownedShares))}
              >
                {isSubmitting
                  ? 'Processing...'
                  : `${tradeMode === 'BUY' ? 'Execute Buy' : 'Execute Sell'} Order`}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
