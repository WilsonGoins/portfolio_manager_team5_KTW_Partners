import { PortfolioValueCard } from "../components/overview/PortfolioValueCard"
import { WatchListCard } from "../components/overview/WatchListCard"
import { AllocationCard } from "../components/overview/AllocationCard.jsx"
import { HoldingsCard } from "../components/overview/HoldingsCard.jsx"
import "./Overview.css"

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

const allocationData = [
  { name: 'Equities', value: 52 },
  { name: 'Fixed Income', value: 23 },
  { name: 'Cash', value: 10 },
  { name: 'Real Estate', value: 9 },
  { name: 'Crypto', value: 6 },
];

const holdingsData = [
    { symbol: 'AAPL', name: 'Apple Inc.', shares: 120, avgCost: 165.20, price: 198.45, mktValue: 23814.00, change: 1.24, alloc: 21.3 },
    { symbol: 'MSFT', name: 'Microsoft Corp.', shares: 60, avgCost: 310.10, price: 421.30, mktValue: 25278.00, change: 0.68, alloc: 22.6 },
    { symbol: 'NVDA', name: 'NVIDIA Corp.', shares: 200, avgCost: 88.40, price: 126.75, mktValue: 25350.00, change: 3.15, alloc: 22.7 },
    { symbol: 'AMZN', name: 'Amazon.com Inc.', shares: 90, avgCost: 145.60, price: 178.20, mktValue: 16038.00, change: -0.42, alloc: 14.4 },
    { symbol: 'GOOGL', name: 'Alphabet Inc.', shares: 75, avgCost: 132.90, price: 165.10, mktValue: 12382.50, change: 0.91, alloc: 11.1 },
    { symbol: 'TSLA', name: 'Tesla Inc.', shares: 40, avgCost: 245.00, price: 219.35, mktValue: 8774.00, change: -1.87, alloc: 7.9 },
]

export function Overview() {
  return (
    <div className="overview-page">
      <div className="overview-main-content">
        <div className="overview-column left-column">
          <PortfolioValueCard data={portfolioValueData} />
          <HoldingsCard data={holdingsData} />
        </div>

        <div className="overview-column right-column">
          <WatchListCard data={watchlistData} />
          <AllocationCard data={allocationData} />
        </div>
      </div>
    </div>
  )
}
