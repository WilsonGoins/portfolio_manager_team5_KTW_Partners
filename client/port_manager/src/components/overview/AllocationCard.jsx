import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import './AllocationCard.css';

const COLORS = ['#008080', '#56a3a3', '#8ac2c2', '#aedbdb', '#6f42c1'];

export function AllocationCard({ data }) {
  const chartData = useMemo(() => {
    if (!data) return [];


    return Object.entries(data).map(([name, value]) => ({
      name,
      value: typeof value === 'number' ? Number(value.toFixed(1)) : 0,
    }));
  }, [data]);

  if (!chartData.length) {
    return (
      <div className="card allocation-card">
        <h3>Allocation</h3>
        <p style={{ color: '#718096', padding: '16px' }}>No allocation data available.</p>
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
              fill="#8884d8"
              paddingAngle={0}
              dataKey="value"
              startAngle={90}
              endAngle={450}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${entry.name}-${index}`} 
                  fill={COLORS[index % COLORS.length]} 
                  stroke="none" 
                />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="allocation-legend">
        {chartData.map((entry, index) => (
          <div key={entry.name} className="legend-item">
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <span 
                className="legend-icon" 
                style={{ backgroundColor: COLORS[index % COLORS.length] }} 
              />
              <span className="legend-label">{entry.name}</span>
            </div>
            <span className="legend-value">{entry.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
