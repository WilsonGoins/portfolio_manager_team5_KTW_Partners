import React, { useMemo, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { formatHoldingType } from '../../utils/holdingType';
import './AllocationCard.css';

const COLORS = ['#008080', '#56a3a3', '#8ac2c2', '#aedbdb', '#6f42c1'];

const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function AllocationTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;

  const slice = payload[0].payload;
  return (
    <div className="allocation-tooltip">
      <div className="allocation-tooltip-type">
        <span className="legend-icon" style={{ backgroundColor: slice.fill }} />
        {formatHoldingType(slice.label)}
      </div>
      <div className="allocation-tooltip-value">{currency.format(slice.market_value)}</div>
      <div className="allocation-tooltip-pct">{slice.allocation_pct.toFixed(1)}% of portfolio</div>
    </div>
  );
}

// dataByType groups holdings by asset type (Cash/Equity/ETF/...); dataBySector
// groups the same holdings by Yahoo Finance sector (Technology/Healthcare/...).
// Both are already-aggregated [{label, market_value, allocation_pct}] lists
// from the backend, so this component just switches which one it renders.
export function AllocationCard({ dataByType, dataBySector }) {
  const [groupBy, setGroupBy] = useState('type');

  const activeData = groupBy === 'type' ? dataByType : dataBySector;

  // colour is keyed to the slice's position in the label-sorted list the API
  // sends, so a slice keeps its colour even as its share of the portfolio moves
  const chartData = useMemo(
    () => (activeData ?? []).map((slice, index) => ({
      ...slice,
      fill: COLORS[index % COLORS.length],
    })),
    [activeData],
  );

  // The list below the chart reads largest-first, which is the order someone
  // scanning for "where is my money" wants. Sorted here rather than upstream on
  // purpose: the colours above are keyed to each slice's position in the API's
  // label-sorted list, so sorting before the fill is attached would repaint the
  // whole chart whenever two slices swapped places. Sorting a copy afterwards
  // reorders the rows while every slice keeps the colour it already had.
  const legendData = useMemo(
    () => [...chartData].sort((a, b) => b.allocation_pct - a.allocation_pct),
    [chartData],
  );

  return (
    <div className="card allocation-card">
      <div className="allocation-card-header">
        <h3>Allocation</h3>
        <div className="allocation-toggle" role="tablist" aria-label="Group allocation by">
          <button
            type="button"
            role="tab"
            aria-selected={groupBy === 'type'}
            className={`allocation-toggle-btn ${groupBy === 'type' ? 'active' : ''}`}
            onClick={() => setGroupBy('type')}
          >
            Type
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={groupBy === 'sector'}
            className={`allocation-toggle-btn ${groupBy === 'sector' ? 'active' : ''}`}
            onClick={() => setGroupBy('sector')}
          >
            Sector
          </button>
        </div>
      </div>

      {!chartData.length ? (
        <p className="allocation-empty-message">No allocation data available.</p>
      ) : (
        <>
          <div className="allocation-chart-container" style={{ height: '220px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={0}
                  dataKey="market_value"
                  nameKey="label"
                  startAngle={90}
                  endAngle={450}
                >
                  {chartData.map((entry) => (
                    <Cell key={entry.label} fill={entry.fill} stroke="none" />
                  ))}
                </Pie>
                <Tooltip content={<AllocationTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="allocation-table">
            <div className="allocation-header">
              <span>{groupBy === 'type' ? 'Type' : 'Sector'}</span>
              <span>Value</span>
            </div>

            <div className="allocation-rows">
              {legendData.map((entry) => (
                <div key={entry.label} className="allocation-row">
                  <div className="allocation-identity">
                    <span className="legend-icon" style={{ backgroundColor: entry.fill }} />
                    <span className="allocation-type">{formatHoldingType(entry.label)}</span>
                  </div>
                  <div className="allocation-figures">
                    <span className="allocation-value">{currency.format(entry.market_value)}</span>
                    <span className="allocation-pct">{entry.allocation_pct.toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

