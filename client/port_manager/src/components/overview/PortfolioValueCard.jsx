import React, { useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './PortfolioValueCard.css';

export function PortfolioValueCard({ data }) {
  const [activeTimeframe, setActiveTimeframe] = useState('1M');
  // const laconst currentChartData = timeframeData[activeTimeframe];testValue = data[""]
  const currentChartData = data[activeTimeframe];
  const latestValue = "$482,930.18";
  const todayChange = "+$12,340.55 (+2.62%) Today";

  return (
    <div className="card portfolio-value-card">
      <div className="card-header">
        <div>
          <h3>Total Portfolio Value</h3>
          <div className="portfolio-value-main">{latestValue}</div>
          <span className="portfolio-value-change positive">{todayChange}</span>
        </div>
        
        <div className="timeframe-selector">
          {['1D', '1W', '1M', 'YTD', '1Y'].map((tf) => (
            <button
              key={tf}
              className={activeTimeframe === tf ? 'active' : ''}
              onClick={() => setActiveTimeframe(tf)}>
              {tf}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-container" style={{ height: '240px', marginTop: '24px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={currentChartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
            <XAxis dataKey="date" hide />
            <YAxis hide domain={['dataMin - 50000', 'auto']} />
            
            <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#008080" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#008080" stopOpacity={0}/>
                </linearGradient>
            </defs>
            <Area type="monotone" dataKey="value" stroke="#008080" strokeWidth={2} fillOpacity={1} fill="url(#colorValue)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
