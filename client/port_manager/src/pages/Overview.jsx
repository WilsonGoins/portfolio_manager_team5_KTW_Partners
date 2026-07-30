import React, { useState, useEffect } from "react";
import { PortfolioValueCard } from "../components/overview/PortfolioValueCard";
import { WatchListCard } from "../components/overview/WatchListCard";
import { AllocationCard } from "../components/overview/AllocationCard.jsx";
import { HoldingsCard } from "../components/overview/HoldingsCard.jsx";
import { OverviewSkeleton } from "../components/overview/OverviewSkeleton.jsx";
import { useDataFreshness } from "../context/DataFreshness";
import "./Overview.css";

// The error state is the same shape in all four slots, so the cards differ only
// by heading. Kept out of the grid's JSX to keep the three states readable.
function ErrorCard({ className, title, message }) {
  return (
    <div className={`card ${className}`}>
      <h3>{title}</h3>
      <p style={{ color: '#e53e3e', padding: '16px' }}>Error loading data: {message}</p>
    </div>
  );
}

export function Overview() {
  const [holdingsData, setHoldingsData] = useState([]);
  const [allocationData, setAllocationData] = useState([]);
  const [portfolioHistory, setPortfolioHistory] = useState([]);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [topMovers, setTopMovers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const { refreshToken, setLastUpdated, setIsRefreshing } = useDataFreshness();

  useEffect(() => {
    let cancelled = false;

    async function fetchOverviewData() {
      // Only the very first load blanks the cards out. A refresh from the navbar
      // leaves the current numbers up until the new ones arrive.
      if (refreshToken === 0) setIsLoading(true);
      setIsRefreshing(true);

      try {
        const response = await fetch('/api/overview');

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const overviewData = await response.json();
        if (cancelled) return;

        setHoldingsData(overviewData.HoldingsTable || []);
        setAllocationData(overviewData.Allocations || []);
        setPortfolioHistory(overviewData.PortfolioHistory || []);
        setPortfolioSummary(overviewData.PortfolioSummary || null);
        setTopMovers(overviewData.TopMovers || []);
        setLastUpdated(overviewData.LastUpdated || new Date().toISOString());
        setError(null);
      } catch (err) {
        if (cancelled) return;
        console.error("Failed to fetch overview data:", err);
        setError(err.message);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
          setIsRefreshing(false);
        }
      }
    }

    fetchOverviewData();

    return () => {
      cancelled = true;
    };
  }, [refreshToken, setLastUpdated, setIsRefreshing]);

  return (
    <div className="overview-page">
      {/* One 2x2 grid rather than two independent columns, so each row's cards
          share a top edge no matter how tall the row above them grows.
          DOM order is row-major: top-left, top-right, bottom-left, bottom-right. */}
      <div className="overview-main-content">
        {isLoading ? (
          <OverviewSkeleton />
        ) : error ? (
          <>
            <ErrorCard className="portfolio-value-card" title="Total Portfolio Value" message={error} />
            <ErrorCard className="watchlist-card" title="Watchlist" message={error} />
            <ErrorCard className="holdings-card" title="Holdings" message={error} />
            <ErrorCard className="allocation-card" title="Allocation" message={error} />
          </>
        ) : (
          <>
            <PortfolioValueCard data={portfolioHistory} summary={portfolioSummary} />
            <WatchListCard data={topMovers} />
            <HoldingsCard data={holdingsData} />
            <AllocationCard data={allocationData} />
          </>
        )}
      </div>
    </div>
  );
}
