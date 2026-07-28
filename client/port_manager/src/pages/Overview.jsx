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

const allocationData = {
  'Equity': 52.0,
  'Fixed Income': 23.0,
  'Cash': 10.0,
  'Real Estate': 9.0,
  'Crypto': 6.0,
};

const holdingsData = [
  {
    symbol: 'AAPL',
    name: 'Apple Inc.',
    h_type: 'Equity',
    num_shares: 120,
    curr_price: 198.45,
    previous_close: 196.01,
    market_value: 23814.00,
    change_since_close: 292.80,
    allocation_pct: 21.3
  },
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corp.',
    h_type: 'Equity',
    num_shares: 200,
    curr_price: 126.75,
    previous_close: 122.88,
    market_value: 25350.00,
    change_since_close: 774.00,
    allocation_pct: 22.7
  },
  {
    symbol: 'cash_value',
    name: 'Cash',
    h_type: 'Cash',
    num_shares: null, // Use null instead of string "--" for safer JS formatting
    curr_price: null,
    previous_close: null,
    market_value: 10000.00,
    change_since_close: null,
    allocation_pct: 10.0
  }
];

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
