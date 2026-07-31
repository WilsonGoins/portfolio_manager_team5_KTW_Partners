import React, { useMemo } from 'react';
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
        {formatHoldingType(slice.h_type)}
      </div>
      <div className="allocation-tooltip-value">{currency.format(slice.market_value)}</div>
      <div className="allocation-tooltip-pct">{slice.allocation_pct.toFixed(1)}% of portfolio</div>
    </div>
  );
}

export function AllocationCard({ data }) {
  // colour is keyed to the slice's position in the type-sorted list the API sends,
  // so a type keeps its colour even as its share of the portfolio moves around
  const chartData = useMemo(
    () => (data ?? []).map((slice, index) => ({
      ...slice,
      fill: COLORS[index % COLORS.length],
    })),
    [data],
  );

  if (!chartData.length) {
    return (
      <div className="card allocation-card">
        <h3>Allocation</h3>
        <p className="allocation-empty-message">No allocation data available.</p>
      </div>
    );
  }

  return (
    <div className="card allocation-card">
      <h3>Allocation</h3>
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
              nameKey="h_type"
              startAngle={90}
              endAngle={450}
            >
              {chartData.map((entry) => (
                <Cell key={entry.h_type} fill={entry.fill} stroke="none" />
              ))}
            </Pie>
            <Tooltip content={<AllocationTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="allocation-table">
        <div className="allocation-header">
          <span>Type</span>
          <span>Value</span>
        </div>

        {chartData.map((entry) => (
          <div key={entry.h_type} className="allocation-row">
            <div className="allocation-identity">
              <span className="legend-icon" style={{ backgroundColor: entry.fill }} />
              <span className="allocation-type">{formatHoldingType(entry.h_type)}</span>
            </div>
            <div className="allocation-figures">
              <span className="allocation-value">{currency.format(entry.market_value)}</span>
              <span className="allocation-pct">{entry.allocation_pct.toFixed(1)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
