import React from 'react';
import './Skeleton.css';

export function SecurityCardSkeleton() {
  return (
    <div className="security-card">
      <div className="card-top-row">
        <div>
          <div className="security-title-group" style={{ gap: '8px', marginBottom: '8px' }}>
            <div className="skeleton-box" style={{ width: '80px', height: '24px' }} />
            <div className="skeleton-box" style={{ width: '50px', height: '20px' }} />
          </div>
          <div className="skeleton-box" style={{ width: '140px', height: '16px' }} />
        </div>

        <div className="price-group" style={{ alignItems: 'flex-end' }}>
          <div className="skeleton-box" style={{ width: '70px', height: '12px', marginBottom: '6px' }} />
          <div className="skeleton-box" style={{ width: '110px', height: '24px' }} />
        </div>
      </div>

      <div className="graph-section" style={{ marginTop: '16px' }}>
        <div className="graph-header" style={{ marginBottom: '12px' }}>
          <div className="skeleton-box" style={{ width: '120px', height: '16px' }} />
          <div className="skeleton-box" style={{ width: '150px', height: '24px' }} />
        </div>
        <div className="chart-wrapper">
          <div className="skeleton-box" style={{ width: '100%', height: '100px' }} />
        </div>
      </div>

      <div className="metrics-row" style={{ marginTop: '16px' }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="metric-item">
            <div className="skeleton-box" style={{ width: '50px', height: '12px', marginBottom: '6px' }} />
            <div className="skeleton-box" style={{ width: '40px', height: '16px' }} />
          </div>
        ))}
      </div>
    </div>
  );
}
