import React, { useState, useEffect } from "react";
import { PortfolioValueCard } from "../components/overview/PortfolioValueCard";
import { WatchListCard } from "../components/overview/WatchListCard";
import { AllocationCard } from "../components/overview/AllocationCard.jsx";
import { HoldingsCard } from "../components/overview/HoldingsCard.jsx";
import "./Overview.css";

const portfolioValueData = {
  '1D': [
    { date: '9:30 AM', value: 478000 },
    { date: '11:00 AM', value: 479200 },
    { date: '1:00 PM', value: 480500 },
    { date: '3:00 PM', value: 481000 },
    { date: '4:00 PM', value: 482930.18 },
  ],
  '1W': [
    { date: 'Mon', value: 468000 },
    { date: 'Tue', value: 471000 },
    { date: 'Wed', value: 469500 },
    { date: 'Thu', value: 477000 },
    { date: 'Fri', value: 482930.18 },
  ],
  '1M': [
    { date: 'Week 1', value: 450000 },
    { date: 'Week 2', value: 462000 },
    { date: 'Week 3', value: 458000 },
    { date: 'Week 4', value: 482930.18 },
  ],
  'YTD': [
    { date: 'Jan', value: 410000 },
    { date: 'Mar', value: 435000 },
    { date: 'May', value: 420000 },
    { date: 'Jul', value: 482930.18 },
  ],
  '1Y': [
    { date: 'Q1', value: 390000 },
    { date: 'Q2', value: 420000 },
    { date: 'Q3', value: 445000 },
    { date: 'Q4', value: 482930.18 },
  ],
};

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
          <PortfolioValueCard data={portfolioValueData} />
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
