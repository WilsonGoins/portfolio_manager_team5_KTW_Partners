import React, { useState, useEffect } from "react";
import { BiggestMoversCard } from "../components/analytics/BiggestMoversCard";
import "./Analytics.css";

export function Analytics() {
  const [moversData, setMoversData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchMoversData() {
      try {
        setIsLoading(true);
        const response = await fetch('/api/analytics/movers');

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        setMoversData(data);
      } catch (err) {
        console.error("Failed to fetch analytics movers data:", err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchMoversData();
  }, []);

  return (
    <div className="analytics-page">
      <h2 className="analytics-page-title">Analytics</h2>

      <div className="analytics-main-content">
        {isLoading ? (
          <div className="card movers-card">
            <h3>Biggest Movers</h3>
            <p style={{ color: '#718096', padding: '16px' }}>Loading movers...</p>
          </div>
        ) : error ? (
          <div className="card movers-card">
            <h3>Biggest Movers</h3>
            <p style={{ color: '#e53e3e', padding: '16px' }}>Error loading data: {error}</p>
          </div>
        ) : (
          <BiggestMoversCard data={moversData} />
        )}

        {/* Other Analytics widgets (volatility, max drawdown, S&P 500
            comparison, etc.) get added here as sibling cards. */}
      </div>
    </div>
  );
}
