import { useEffect, useState, useCallback } from 'react';
import { Search } from './Search';
import { SecurityCard } from './SecurityCard';
import "./ExploreSecurities.css";

export function ExploreSecurities() {
  const [securities, setSecurities] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showingQueryResults, setShowingQueryResults] = useState(false)
  const [searchText, setSearchText] = useState('');

  const fetchTopMovers = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);

      const response = await fetch('/api/top-movers');

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const watchlistData = await response.json();
      setSecurities(watchlistData);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch top movers:", err);
      setError(err.message);
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if(!loading) {
      setShowingQueryResults(searchQuery.trim() !== '');
      setSearchText(searchQuery);
    }
  }, [loading])

  useEffect(() => {
    let isMounted = true;

    if (searchQuery.trim() === '') {
      fetchTopMovers(true);

      const intervalId = setInterval(() => {
        if (isMounted) fetchTopMovers(false);
      }, 60 * 1000);

      return () => {
        isMounted = false;
        clearInterval(intervalId);
      };
    }
  }, [searchQuery, fetchTopMovers]);

  const handleBackendSearch = async (query) => {
    if (!query.trim()) {
      fetchTopMovers(true);
      setShowingQueryResults(false);
      return;
    }

    setSearchText(query);

    setLoading(true);
    try {
      const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);

      if (!response.ok) throw new Error(`Search failed: ${response.status}`);

      const data = await response.json();
      setSecurities(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      console.error('Failed to search securities:', err);

      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleQueryChange = (newQuery) => {
    setSearchQuery(newQuery);
    if (newQuery.trim() === '') {
      fetchTopMovers(true);
    }
  };

  return (
    <div className="explore-securities-container">
      <Search
        query={searchQuery}
        onQueryChange={handleQueryChange}
        onSearch={handleBackendSearch}
        isLoading={loading}
      />

      {error && <div className="error-banner">{error}</div>}

      {showingQueryResults ? (
      <h3>Search results for {searchText}</h3>
      ) : (
      <h3>Top 5 Movers Of The Day...</h3>
      )}

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
