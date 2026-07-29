import React, { useState, useEffect } from "react";
import { PortfolioValueCard } from "../components/overview/PortfolioValueCard";
import { WatchListCard } from "../components/overview/WatchListCard";
import { AllocationCard } from "../components/overview/AllocationCard.jsx";
import { HoldingsCard } from "../components/overview/HoldingsCard.jsx";
import "./Overview.css";

export function Overview() {
  const [holdingsData, setHoldingsData] = useState([]);
  const [allocationData, setAllocationData] = useState([]);
  const [portfolioHistory, setPortfolioHistory] = useState([]);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
  const [topMovers, setTopMovers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchOverviewData() {
      try {
        setIsLoading(true);
        const response = await fetch('/api/overview'); 
        
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const overviewData = await response.json();
        
        setHoldingsData(overviewData.HoldingsTable || []);
        setAllocationData(overviewData.Allocations || []);
        setPortfolioHistory(overviewData.PortfolioHistory || []);
        setPortfolioSummary(overviewData.PortfolioSummary || null);
        setTopMovers(overviewData.TopMovers || []);
      } catch (err) {
        console.error("Failed to fetch overview data:", err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchOverviewData();
  }, []);

  return (
    <div className="overview-page">
      {/* One 2x2 grid rather than two independent columns, so each row's cards
          share a top edge no matter how tall the row above them grows.
          DOM order is row-major: top-left, top-right, bottom-left, bottom-right. */}
      <div className="overview-main-content">
        {isLoading ? (
          <div className="card portfolio-value-card">
            <h3>Total Portfolio Value</h3>
            <p style={{ color: '#718096', padding: '16px' }}>Loading portfolio value...</p>
          </div>
        ) : error ? (
          <div className="card portfolio-value-card">
            <h3>Total Portfolio Value</h3>
            <p style={{ color: '#e53e3e', padding: '16px' }}>Error loading data: {error}</p>
          </div>
        ) : (
          <PortfolioValueCard data={portfolioHistory} summary={portfolioSummary} />
        )}

        {isLoading ? (
          <div className="card watchlist-card">
            <h3>Watchlist</h3>
            <p style={{ color: '#718096', padding: '16px' }}>Loading movers...</p>
          </div>
        ) : error ? (
          <div className="card watchlist-card">
            <h3>Watchlist</h3>
            <p style={{ color: '#e53e3e', padding: '16px' }}>Error loading data: {error}</p>
          </div>
        ) : (
          <WatchListCard data={topMovers} />
        )}

        {isLoading ? (
          <div className="card holdings-card">
            <h3>Holdings</h3>
            <p style={{ color: '#718096', padding: '16px' }}>Loading holdings...</p>
          </div>
        ) : error ? (
          <div className="card holdings-card">
            <h3>Holdings</h3>
            <p style={{ color: '#e53e3e', padding: '16px' }}>Error loading data: {error}</p>
          </div>
        ) : (
          <HoldingsCard data={holdingsData} />
        )}

        {isLoading ? (
          <div className="card allocation-card">
            <h3>Allocation</h3>
            <p style={{ color: '#718096', padding: '16px' }}>Loading allocation...</p>
          </div>
        ) : error ? (
          <div className="card allocation-card">
            <h3>Allocation</h3>
            <p style={{ color: '#e53e3e', padding: '16px' }}>Error loading data: {error}</p>
          </div>
        ) : (
          <AllocationCard data={allocationData} />
        )}
      </div>
    </div>
  );
}
