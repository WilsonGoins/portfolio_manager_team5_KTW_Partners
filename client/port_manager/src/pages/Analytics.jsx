import React, { useState, useEffect } from "react";
import { RiskCard } from "../components/analytics/RiskCard";
import { useDataFreshness } from "../context/DataFreshness";
import "./Analytics.css";

function MessageCard({ title, message, tone }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <p style={{ color: tone === 'error' ? '#e53e3e' : '#718096', padding: '16px' }}>
        {message}
      </p>
    </div>
  );
}

export function Analytics() {
  const [riskData, setRiskData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const { refreshToken, setLastUpdated, setIsRefreshing } = useDataFreshness();

  // This page reads the same yahoo finance quotes the Overview does, so it takes
  // part in the navbar's refresh rather than sitting there stale while the
  // button appears to do nothing.
  useEffect(() => {
    let cancelled = false;

    async function fetchRiskData() {
      if (refreshToken === 0) setIsLoading(true);
      setIsRefreshing(true);

      try {
        const response = await fetch('/api/risk');

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        if (cancelled) return;

        setRiskData(data);
        // /api/risk has no timestamp of its own, but the quotes behind it were
        // just fetched, so the navbar's "prices updated" label is accurate here.
        setLastUpdated(new Date().toISOString());
        setError(null);
      } catch (err) {
        if (cancelled) return;
        console.error("Failed to fetch risk data:", err);
        setError(err.message);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
          setIsRefreshing(false);
        }
      }
    }

    fetchRiskData();

    return () => {
      cancelled = true;
    };
  }, [refreshToken, setLastUpdated, setIsRefreshing]);

  return (
    <div className="analytics-page">
      <h2 className="analytics-page-title">Advanced Analytics</h2>

      {/* One column for now. The grid is here so the volatility and concentration
          cards can drop in beside this one without the page being rebuilt. */}
      <div className="analytics-main-content">
        {isLoading ? (
          <MessageCard title="Portfolio Risk" message="Loading risk data..." />
        ) : error ? (
          <MessageCard title="Portfolio Risk" message={`Error loading data: ${error}`} tone="error" />
        ) : /* holdings always carries a cash row, so "empty" means nothing is
               actually invested -- a beta of 0 over one muted cash row would be
               a card with nothing to say */
          !riskData.holdings.some((row) => row.h_type !== 'Cash') ? (
          <MessageCard
            title="Portfolio Risk"
            message="No holdings yet. Buy a security to see how much market risk your portfolio carries."
          />
        ) : (
          <RiskCard data={riskData} />
        )}
      </div>
    </div>
  );
}
