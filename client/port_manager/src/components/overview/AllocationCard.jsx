import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import './AllocationCard.css';

const COLORS = ['#008080', '#56a3a3', '#8ac2c2', '#aedbdb', '#6f42c1'];

export function AllocationCard({ data }) {
  return (
    <div className="card allocation-card">
      <h3>Allocation</h3>
      <div className="allocation-chart-container" style={{ height: '220px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
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
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="none" />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
      </div>

      <div className="allocation-legend">
        {data.map((entry, index) => (
          <div key={entry.name} className="legend-item">
            <div style={{display: 'flex', gap: '8px'}}>
                <span className="legend-icon" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                <span className="legend-label">{entry.name}</span>
            </div>
            <span className="legend-value">{entry.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
