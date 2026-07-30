import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

// The navbar lives in the Layout, but the pages under it are the ones that actually
// talk to the API. This context is the seam between them: pages report when their
// yahoo finance data landed, and the navbar's refresh button bumps a token the pages
// re-fetch on.
const DataFreshnessContext = createContext(null);

export function DataFreshnessProvider({ children }) {
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshToken, setRefreshToken] = useState(0);

  const requestRefresh = useCallback(() => {
    setRefreshToken((token) => token + 1);
  }, []);

  const value = useMemo(() => ({
    lastUpdated,
    setLastUpdated,
    isRefreshing,
    setIsRefreshing,
    refreshToken,
    requestRefresh,
  }), [lastUpdated, isRefreshing, refreshToken, requestRefresh]);

  return (
    <DataFreshnessContext.Provider value={value}>
      {children}
    </DataFreshnessContext.Provider>
  );
}

export function useDataFreshness() {
  const context = useContext(DataFreshnessContext);
  if (!context) {
    throw new Error("useDataFreshness must be used inside a DataFreshnessProvider");
  }
  return context;
}
