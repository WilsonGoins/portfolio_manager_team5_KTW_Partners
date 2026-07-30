import React from 'react';
import './Search.css';

export function Search({ query, onQueryChange, onSearch, isLoading = false, placeholder = 'Search tickers, companies, or keywords...' }) {

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && onSearch) {
      onSearch(query.trim());
    }
  };

  const handleClear = () => {
    onQueryChange('');
  };

  return (
    <div className="search-container">
      <form className="search-form" onSubmit={handleSubmit}>
        <div className="search-icon-wrapper">
          <svg className="search-icon" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
        </div>

        <input
          type="text"
          className="search-input"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={placeholder}
        />

        <div className="search-actions">
          {isLoading && <div className="spinner" aria-label="Loading search results" />}

          {query && !isLoading && (
            <button type="button" className="clear-btn" onClick={handleClear} aria-label="Clear input">
              ✕
            </button>
          )}

          <button type="submit" className="search-submit-btn" disabled={!query || isLoading}>
            Search
          </button>
        </div>
      </form>
    </div>
  );
}
