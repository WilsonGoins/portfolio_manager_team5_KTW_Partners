import React, { useMemo, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './PortfolioValueCard.css';

const TIMEFRAMES = ['1D', '1W', '1M', 'YTD', '1Y'];

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

// Axis ticks are short so they don't crowd the plot: $90K, $129.3K
const compactCurrency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  notation: 'compact',
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});

const shortDate = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
});

const longDate = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'UTC',
});

// Round tick values covering [min, max] -- steps snap to 1/2/5 x a power of ten
// so the axis reads $90K / $100K / $110K rather than whatever the data ends on.
function niceTicks(min, max, count = 5) {
  const span = max - min || Math.abs(max) || 1;
  const rawStep = span / (count - 1);
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const normalized = rawStep / magnitude;
  const step =
    (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * magnitude;

  const ticks = [];
  const upper = Math.ceil(max / step) * step;
  for (let t = Math.floor(min / step) * step; t <= upper + step / 2; t += step) {
    ticks.push(Math.round(t * 1e6) / 1e6);
  }
  return ticks;
}

// Earliest date ("YYYY-MM-DD") a timeframe should include, counted back from the
// most recent point rather than from today, so the chart still fills in if the
// snapshots are lagging. Dates stay as strings -- ISO dates compare correctly.
function cutoffDate(timeframe, latestDate) {
  const d = new Date(`${latestDate}T00:00:00Z`);

  switch (timeframe) {
    case '1D':
      d.setUTCDate(d.getUTCDate() - 1);
      break;
    case '1W':
      d.setUTCDate(d.getUTCDate() - 7);
      break;
    case '1M':
      d.setUTCMonth(d.getUTCMonth() - 1);
      break;
    case 'YTD':
      return `${d.getUTCFullYear()}-01-01`;
    case '1Y':
      d.setUTCFullYear(d.getUTCFullYear() - 1);
      break;
    default:
      return null;
  }

  return d.toISOString().slice(0, 10);
}

export function PortfolioValueCard({ data, summary }) {
  const [activeTimeframe, setActiveTimeframe] = useState('1M');

  const currentChartData = useMemo(() => {
    const history = data ?? [];
    if (!history.length) return [];

    const cutoff = cutoffDate(activeTimeframe, history[history.length - 1].date);
    return cutoff ? history.filter((point) => point.date >= cutoff) : history;
  }, [data, activeTimeframe]);

  const yTicks = useMemo(() => {
    if (!currentChartData.length) return [];

    const values = currentChartData.map((point) => point.value);
    return niceTicks(Math.min(...values), Math.max(...values));
  }, [currentChartData]);

  const latestValue = summary ? currency.format(summary.total_value) : '--';

  const isPositive = (summary?.day_change ?? 0) >= 0;
  const todayChange = summary
    ? `${isPositive ? '+' : '-'}${currency.format(Math.abs(summary.day_change))} ` +
      `(${isPositive ? '+' : ''}${summary.day_change_pct.toFixed(2)}%) Today`
    : '--';

  return (
    <div className="card portfolio-value-card">
      <div className="card-header">
        <div>
          <h3>Total Portfolio Value</h3>
          <div className="portfolio-value-main">{latestValue}</div>
          <span className={`portfolio-value-change ${isPositive ? 'positive' : 'negative'}`}>
            {todayChange}
          </span>
        </div>

        <div className="timeframe-selector">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              className={activeTimeframe === tf ? 'active' : ''}
              onClick={() => setActiveTimeframe(tf)}>
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* height covers the plot plus the x-axis band, so ticks aren't clipped */}
      <div className="chart-container" style={{ height: '280px', marginTop: '24px' }}>
        {currentChartData.length < 2 ? (
          <p className="chart-empty-message">
            Not enough history to chart {activeTimeframe}.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={currentChartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tickFormatter={(date) => shortDate.format(new Date(`${date}T00:00:00Z`))}
                tick={{ fill: '#718096', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#e2e8f0' }}
                minTickGap={32}
                tickMargin={8}
              />
              <YAxis
                ticks={yTicks}
                domain={[yTicks[0], yTicks[yTicks.length - 1]]}
                tickFormatter={(value) => compactCurrency.format(value)}
                tick={{ fill: '#718096', fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={56}
              />
              <Tooltip
                formatter={(value) => [currency.format(value), 'Value']}
                labelFormatter={(date) => longDate.format(new Date(`${date}T00:00:00Z`))}
                contentStyle={{
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  fontSize: '0.85rem',
                }}
              />

              <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#008080" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#008080" stopOpacity={0}/>
                  </linearGradient>
              </defs>
              <Area type="monotone" dataKey="value" stroke="#008080" strokeWidth={2} fillOpacity={1} fill="url(#colorValue)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
