import React from 'react';
import '../explore/Skeleton.css';

export function DetailsSkeleton() {
  return (
    <div className="details-container">
      <div className="skeleton-box" style={{ width: '80px', height: '20px', marginBottom: '20px' }} />

      <div className="details-grid">
        <div className="main-panel">
          <div className="card chart-card">
            <div className="chart-header">
              <div>
                <div className="skeleton-box skeleton-header-title" />
                <div className="skeleton-box skeleton-text-sm" />
                <div className="skeleton-box skeleton-price" />
              </div>
              <div className="skeleton-box" style={{ width: '160px', height: '32px' }} />
            </div>
            <div className="skeleton-box skeleton-chart" />
          </div>

          <div className="card stats-card">
            <div className="skeleton-box" style={{ width: '100px', height: '16px', marginBottom: '18px' }} />
            <div className="stats-grid">
              <div className="skeleton-box skeleton-stat-box" />
              <div className="skeleton-box skeleton-stat-box" />
              <div className="skeleton-box skeleton-stat-box" />
              <div className="skeleton-box skeleton-stat-box" />
            </div>
          </div>
        </div>

        <div className="side-panel">
          <div className="card position-card">
            <div className="skeleton-box" style={{ width: '120px', height: '16px', marginBottom: '16px' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="skeleton-box" style={{ height: '20px' }} />
              <div className="skeleton-box" style={{ height: '20px' }} />
              <div className="skeleton-box" style={{ height: '20px' }} />
            </div>
          </div>

          <div className="card trade-card">
            <div className="skeleton-box" style={{ width: '100px', height: '16px', marginBottom: '16px' }} />
            <div className="skeleton-box" style={{ height: '36px', marginBottom: '20px' }} />
            <div className="skeleton-box" style={{ height: '40px', marginBottom: '20px' }} />
            <div className="skeleton-box skeleton-button" />
          </div>
        </div>
      </div>
    </div>
  );
}
