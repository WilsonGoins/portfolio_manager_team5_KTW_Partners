import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { useDataFreshness } from "../context/DataFreshness";
import "./Navbar.css";

// "just now" up to a minute, then minutes, then hours, then the clock time --
// past a few hours the exact time is more useful than a growing "8h ago".
function formatElapsed(timestamp, now) {
  const then = new Date(timestamp);
  if (Number.isNaN(then.getTime())) return null;

  const seconds = Math.max(0, Math.round((now - then.getTime()) / 1000));
  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 6) return `${hours}h ago`;

  return then.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function Navbar() {
  const { lastUpdated, isRefreshing, requestRefresh } = useDataFreshness();
  const [now, setNow] = useState(() => Date.now());

  // The label ages on its own, so re-tick while a timestamp is on screen.
  useEffect(() => {
    if (!lastUpdated) return;
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(id);
  }, [lastUpdated]);

  const elapsed = lastUpdated ? formatElapsed(lastUpdated, now) : null;

  return (
    <header className="navbar-container">
      <Link className="navbar-brand" to="/">
        <div className="brand-icon">K</div>
        <span className="brand-name">KTW Partners</span>
      </Link>

      <nav className="navbar-links">
        <NavLink to="/" end>Overview</NavLink>
        <NavLink to="/explore">Explore</NavLink>
        <NavLink to="/analytics">Analytics</NavLink>
        <NavLink to="/transactions">Transactions</NavLink>
        <NavLink to="/analytics">Advanced Analytics</NavLink>
      </nav>

      <div className="navbar-freshness">
        <span className="freshness-label">
          {isRefreshing
            ? "Updating prices…"
            : elapsed
              ? `Prices updated ${elapsed}`
              : "Prices not loaded yet"}
        </span>
        <button
          type="button"
          className="freshness-refresh"
          onClick={requestRefresh}
          disabled={isRefreshing}
          title="Re-fetch quotes from Yahoo Finance"
        >
          Refresh
        </button>
      </div>
    </header>
  );
}
