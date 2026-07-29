import { useEffect, useState } from 'react';
import { Search } from './Search';
import { SecurityCard } from './SecurityCard';
import "./ExploreSecurities.css"

export function ExploreSecurities() {
  const [securities, setSecurities] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

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

  const handleBackendSearch = async (query) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/securities/search?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      setSecurities(data);
    } catch (err) {
      console.error('Failed to search securities:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="explore-securities-container">
      <Search
        query={searchQuery}
        onQueryChange={setSearchQuery}
        onSearch={handleBackendSearch}
        isLoading={loading}
      />
      <div className="securities">
        {securities.map((security) => (
          <SecurityCard key={security.symbol} data={security} />
        ))}
      </div>
    </div>
  );
}
