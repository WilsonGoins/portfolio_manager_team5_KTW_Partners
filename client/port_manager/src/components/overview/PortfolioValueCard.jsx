import React, { useMemo, useState } from 'react';
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
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
  timeZone: 'America/Toronto',
});

const longDate = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  timeZone: 'America/Toronto',
});

const longDateTime = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'America/Toronto',
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
  if (!latestDate) return null;

  const d = new Date(
    latestDate.includes('T') ? latestDate : `${latestDate}T00:00:00Z`
  );

  if (isNaN(d.getTime())) return null;

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

const percent = (value) => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;

function ComparisonTooltip({ active, payload, label, activeTimeframe }) {
  if (!active || !payload?.length || !label) return null;

  const hasTime = label.includes(':') || label.includes('GMT') || label.includes('T');
  const parsedDate = new Date(hasTime ? label : `${label}T00:00:00Z`);

  if (isNaN(parsedDate.getTime())) return null;

  const formattedDate =
    activeTimeframe === '1D'
      ? longDateTime.format(parsedDate)
      : longDate.format(parsedDate);

  return (
    <div className="comparison-tooltip">
      <div className="comparison-tooltip-date">{formattedDate}</div>
      {payload.map(
        (entry) =>
          entry.value != null && (
            <div key={entry.dataKey} className="comparison-tooltip-row">
              <span className="legend-dot" style={{ backgroundColor: entry.stroke }} />
              <span className="comparison-tooltip-label">{entry.name}</span>
              <span className="comparison-tooltip-value">{percent(entry.value)}</span>
            </div>
          )
      )}
    </div>
  );
}

export function PortfolioValueCard({ data, summary }) {
  const [activeTimeframe, setActiveTimeframe] = useState('1M');
  const [showBenchmark, setShowBenchmark] = useState(false);

  const currentChartData = useMemo(() => {
    const history = data ?? [];
    if (!history.length) return [];

    const cutoff = cutoffDate(activeTimeframe, history[history.length - 1].date);
    const filtered = cutoff
      ? history.filter((point) => point.date >= cutoff)
      : history;

    if (activeTimeframe === '1D') {
      return filtered;
    }

    const dailyMap = {};
    filtered.forEach((point) => {
      const dayKey = point.date.slice(0, 10);
      dailyMap[dayKey] = point;
    });

  return Object.values(dailyMap);
}, [data, activeTimeframe]);

  // Both lines are re-anchored to 0% at the *first point of the currently
  // selected timeframe* -- not one fixed anchor for all history -- so
  // switching from 1M to 1Y re-normalizes rather than showing a shrunken
  // corner of a much bigger swing. The benchmark's own anchor is the first
  // point in the slice that actually has a benchmark_value, in case the
  // portfolio's history reaches back further than the benchmark's.
  const comparisonChartData = useMemo(() => {
    if (!showBenchmark || !currentChartData.length) return [];

    const portfolioAnchor = currentChartData[0].value;
    const benchmarkAnchorPoint = currentChartData.find((point) => point.benchmark_value != null);
    const benchmarkAnchor = benchmarkAnchorPoint?.benchmark_value ?? null;

    return currentChartData.map((point) => ({
      date: point.date,
      portfolio_return_pct: portfolioAnchor
        ? (point.value / portfolioAnchor - 1) * 100
        : 0,
      benchmark_return_pct: (benchmarkAnchor && point.benchmark_value != null)
        ? (point.benchmark_value / benchmarkAnchor - 1) * 100
        : null,
    }));
  }, [currentChartData, showBenchmark]);

  const yTicks = useMemo(() => {
    if (!currentChartData.length) return [];

    const values = currentChartData.map((point) => point.value);
    return niceTicks(Math.min(...values), Math.max(...values));
  }, [currentChartData]);

  const latestValue = summary ? currency.format(summary.total_value) : '--';

  const isPositive = (summary?.day_change ?? 0) >= 0;
  console.log(summary);
  const todayChange = summary
    ? `${isPositive ? '+' : '-'}${currency.format(Math.abs(summary.day_change))} ` +
      `(${isPositive ? '+' : ''}${Number(summary.day_change_pct).toFixed(2)}%) Today`
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
      </div>

      <div className="value-card-controls">
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

        <button
          type="button"
          className={`benchmark-toggle ${showBenchmark ? 'active' : ''}`}
          aria-pressed={showBenchmark}
          onClick={() => setShowBenchmark((prev) => !prev)}
        >
          Compare to S&amp;P 500
        </button>
      </div>

      <div className="chart-container" style={{ height: '200px', marginTop: '12px' }}>
        {showBenchmark ? (
          comparisonChartData.length < 2 ? (
            <p className="chart-empty-message">
              Not enough history to chart {activeTimeframe}.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={comparisonChartData} margin={{ top: 10, right: 26, left: 0, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(dateStr) => {
                    if (!dateStr) return '';
                    
                    // Parse directly if it has a timestamp/GMT, otherwise append T00:00:00Z fallback
                    const hasTime = dateStr.includes(':') || dateStr.includes('GMT') || dateStr.includes('T');
                    const parsedDate = new Date(hasTime ? dateStr : `${dateStr}T00:00:00Z`);

                    // Guard against any invalid dates
                    if (isNaN(parsedDate.getTime())) return '';

                    // If activeTimeframe is '1D', display time on the X-axis ticks (e.g., "9:30 AM")
                    if (activeTimeframe === '1D') {
                      return new Intl.DateTimeFormat('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                        timeZone: 'America/Toronto', // Or omit for local browser time
                      }).format(parsedDate);
                    }

                    // Otherwise show short date (e.g., "Aug 3")
                    return shortDate.format(parsedDate);
                  }}
                  tick={{ fill: '#718096', fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: '#e2e8f0' }}
                  minTickGap={32}
                  tickMargin={8}
                />
                <YAxis
                  tickFormatter={(value) => `${value.toFixed(0)}%`}
                  tick={{ fill: '#718096', fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                />
                <Tooltip content={<ComparisonTooltip activeTimeframe={activeTimeframe} />} />

                <Line
                  type="monotone"
                  dataKey="portfolio_return_pct"
                  name="Your Portfolio"
                  stroke="#008080"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="benchmark_return_pct"
                  name="S&P 500"
                  stroke="#64748b"
                  strokeWidth={2}
                  strokeDasharray="4 3"
                  dot={false}
                  connectNulls={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )
        ) : currentChartData.length < 2 ? (
          <p className="chart-empty-message">
            Not enough history to chart {activeTimeframe}.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={currentChartData} margin={{ top: 10, right: 26, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tickFormatter={(dateStr) => {
                  if (!dateStr) return '';
                  const hasTime = dateStr.includes(':') || dateStr.includes('GMT') || dateStr.includes('T');
                  const parsedDate = new Date(hasTime ? dateStr : `${dateStr}T00:00:00Z`);

                  if (isNaN(parsedDate.getTime())) return '';

                  return activeTimeframe === '1D'
                    ? new Intl.DateTimeFormat('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                        timeZone: 'America/Toronto',
                      }).format(parsedDate)
                    : shortDate.format(parsedDate);
                }}
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
                labelFormatter={(dateStr) => {
                  if (!dateStr) return '';

                  const hasTime = dateStr.includes(':') || dateStr.includes('GMT') || dateStr.includes('T');
                  const parsedDate = new Date(hasTime ? dateStr : `${dateStr}T00:00:00Z`);

                  if (isNaN(parsedDate.getTime())) return '';

                  return activeTimeframe === '1D'
                    ? longDateTime.format(parsedDate)
                    : longDate.format(parsedDate);
                }}
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
