import { useEffect, useState } from 'react';
import { Search } from './Search';
import { SecurityCard } from './SecurityCard';

export function ExploreSecurities() {
  const [securities, setSecurities] = useState([]);

  useEffect(() => {
    const fetchSecurities = async () => {

      const mockData = [
        {
          symbol: 'AAPL',
          name: 'Apple Inc.',
          h_type: 'Equity',
          curr_price: 198.45,
          previous_close: 196.01,
          change_since_close: 292.80,
        },
        {
          symbol: 'NVDA',
          name: 'NVIDIA Corp.',
          h_type: 'Equity',
          curr_price: 126.75,
          previous_close: 122.88,
          change_since_close: 774.00,
        },
      ];

      setSecurities(mockData);
    };

    fetchSecurities();
  }, []);

  return (
    <>
      <Search />
      <div className="securities-grid">
        {securities.map((security) => (
          <SecurityCard key={security.symbol} data={security} />
        ))}
      </div>
    </>
  );
}
