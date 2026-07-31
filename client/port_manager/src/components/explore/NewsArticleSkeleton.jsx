import React from 'react';
import './Skeleton.css';

export function NewsArticleSkeleton() {
  return (
    <div className="news-card">
      <div className="img-container">
        <div className="skeleton-box" style={{ width: '100%', height: '100%' }} />
      </div>
      <div className="news-content">
        <div className="news-meta" style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
          <div className="skeleton-box" style={{ width: '90px', height: '14px' }} />
          <div className="skeleton-box" style={{ width: '40px', height: '14px' }} />
        </div>
        <div className="skeleton-box" style={{ width: '90%', height: '16px', marginBottom: '6px' }} />
        <div className="skeleton-box" style={{ width: '65%', height: '16px' }} />
      </div>
    </div>
  );
}
