import React, { useState, useEffect } from "react";
import { RiskCard } from "../components/analytics/RiskCard";
import { BiggestMoversCard } from "../components/analytics/BiggestMoversCard";
import { useDataFreshness } from "../context/DataFreshness";
import "./Analytics.css";

function MessageCard({ className, title, message, tone }) {
  return (
    <div className={`card ${className}`}>
      <h3>{title}</h3>
      <p style={{ color: tone === 'error' ? '#e53e3e' : '#718096', padding: '16px' }}>
        {message}
      </p>
    </div>
  );
}

export function Analytics() {
  const [riskData, setRiskData] = useState(null);
  const [riskError, setRiskError] = useState(null);
  const [moversData, setMoversData] = useState(null);
  const [moversError, setMoversError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const { refreshToken, setLastUpdated, setIsRefreshing } = useDataFreshness();

  // Both cards read the same yahoo finance quotes the Overview does, so the page
  // takes part in the navbar's refresh rather than sitting there stale while the
  // button appears to do nothing.
  useEffect(() => {
    let cancelled = false;

    async function getJson(url) {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Server returned ${response.status}`);
      return response.json();
    }

    async function fetchAnalyticsData() {
      if (refreshToken === 0) setIsLoading(true);
      setIsRefreshing(true);

      // Both requests go out at once rather than one waiting on the other, and
      // allSettled rather than all: the two cards answer different questions
      // from different endpoints, so one failing shouldn't blank out the other.
      const [risk, movers] = await Promise.allSettled([
        getJson('/api/risk'),
        getJson('/api/analytics/movers'),
      ]);

      if (cancelled) return;

      if (risk.status === 'fulfilled') {
        setRiskData(risk.value);
        setRiskError(null);
      } else {
        console.error("Failed to fetch risk data:", risk.reason);
        setRiskError(risk.reason.message);
      }

      if (movers.status === 'fulfilled') {
        setMoversData(movers.value);
        setMoversError(null);
      } else {
        console.error("Failed to fetch movers data:", movers.reason);
        setMoversError(movers.reason.message);
      }

      // neither endpoint stamps a time of its own, but both price the portfolio
      // as they answer, so either one landing means the quotes on screen are current
      if (risk.status === 'fulfilled' || movers.status === 'fulfilled') {
        setLastUpdated(new Date().toISOString());
      }

      setIsLoading(false);
      setIsRefreshing(false);
    }

    fetchAnalyticsData();

    return () => {
      cancelled = true;
    };
  }, [refreshToken, setLastUpdated, setIsRefreshing]);

  // holdings always carries a cash row, so "empty" means nothing is actually
  // invested -- a beta of 0 over one muted cash row would be a card with
  // nothing to say
  const hasPositions = riskData?.holdings?.some((row) => row.h_type !== 'Cash');

  return (
    <div className="analytics-page">
      <h2 className="analytics-page-title">Advanced Analytics</h2>

      {/* Cards are direct grid items in DOM order: risk takes the wide column,
          movers the narrow one. Each renders its own loading and error state, so
          a failure on one endpoint leaves the other card intact. */}
      <div className="analytics-main-content">
        {isLoading ? (
          <MessageCard className="risk-card" title="Portfolio Risk" message="Loading risk data..." />
        ) : riskError ? (
          <MessageCard className="risk-card" title="Portfolio Risk" message={`Error loading data: ${riskError}`} tone="error" />
        ) : !hasPositions ? (
          <MessageCard
            className="risk-card"
            title="Portfolio Risk"
            message="No holdings yet. Buy a security to see how much market risk your portfolio carries."
          />
        ) : (
          <RiskCard data={riskData} />
        )}

        {isLoading ? (
          <MessageCard className="movers-card" title="Biggest Movers" message="Loading movers..." />
        ) : moversError ? (
          <MessageCard className="movers-card" title="Biggest Movers" message={`Error loading data: ${moversError}`} tone="error" />
        ) : (
          <BiggestMoversCard data={moversData} />
        )}
      </div>
    </div>
  );
}
