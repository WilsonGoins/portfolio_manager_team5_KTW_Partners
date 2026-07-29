import { useEffect, useState } from 'react';
import { Search } from './Search';
import { SecurityCard } from './SecurityCard';
import "./ExploreSecurities.css";

export function ExploreSecurities() {
  const [securities, setSecurities] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function fetchSecurities(isInitial = false) {
      if (searchQuery.trim() !== '') return;

      try {
        if (isInitial) setLoading(true);

        const response = await fetch('/api/top-movers');

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const watchlistData = await response.json();

        if (isMounted) {
          setSecurities(watchlistData);
          setError(null);
        }
      } catch (err) {
        console.error("Failed to fetch top movers:", err);
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted && isInitial) setLoading(false);
      }
    }

    fetchSecurities(true);

    const intervalId = setInterval(() => {
      fetchSecurities(false);
    }, 60 * 1000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [searchQuery]);

  const handleBackendSearch = async (query) => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/securities/search?q=${encodeURIComponent(query)}`);
      
      if (!response.ok) throw new Error(`Search failed: ${response.status}`);
      
      const data = await response.json();
      setSecurities(data);
      setError(null);
    } catch (err) {
      console.error('Failed to search securities:', err);
      setError(err.message);
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

      {error && <div className="error-banner">{error}</div>}

      <div className="securities">
        {!loading && securities.length === 0 ? (
          <p className="no-results">No securities found.</p>
        ) : (
          securities.map((security) => (
            <SecurityCard key={security.symbol} data={security} />
          ))
        )}
      </div>
    </div>
  );
}
