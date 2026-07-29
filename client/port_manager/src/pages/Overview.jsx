import React, { useState, useEffect } from "react";
import { PortfolioValueCard } from "../components/overview/PortfolioValueCard";
import { WatchListCard } from "../components/overview/WatchListCard";
import { AllocationCard } from "../components/overview/AllocationCard.jsx";
import { HoldingsCard } from "../components/overview/HoldingsCard.jsx";
import "./Overview.css";

const watchlistData = [
  { symbol: 'AMD', price: 142.30, change: 2.10 },
  { symbol: 'NFLX', price: 645.80, change: -0.55 },
  { symbol: 'META', price: 498.20, change: 1.35 },
  { symbol: 'BA', price: 178.90, change: -2.20 },
  { symbol: 'JPM', price: 205.60, change: 0.48 },
];

export function Overview() {
  const [holdingsData, setHoldingsData] = useState([]);
  const [allocationData, setAllocationData] = useState({});
  const [portfolioHistory, setPortfolioHistory] = useState([]);
  const [portfolioSummary, setPortfolioSummary] = useState(null);
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
        setAllocationData(overviewData.AllocationsDict || {});
        setPortfolioHistory(overviewData.PortfolioHistory || []);
        setPortfolioSummary(overviewData.PortfolioSummary || null);
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
      <div className="overview-main-content">
        <div className="overview-column left-column">
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
        </div>

        <div className="overview-column right-column">
          <WatchListCard data={watchlistData} />
          {isLoading ? (
            <div className="card allocation-card">
              <h3>Allocation</h3>
              <p style={{ color: '#718096', padding: '16px' }}>Loading allocation...</p>
            </div>
          ) : (
            <AllocationCard data={allocationData} />
          )}
        </div>
      </div>
    </div>
  );
}
