// src/components/Layout.jsx
import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css"; // optional custom styling

export function Layout() {
  return (
    <div>
      <nav className="navbar">
        <div className="logo">My App</div>
        <div className="nav-links">
          <NavLink to="/" end>Overview</NavLink>
          <NavLink to="/holdings">Holdings</NavLink>
          <NavLink to="/explore">Explore</NavLink>
          <NavLink to="/transactions">Transactions</NavLink>
        </div>
      </nav>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
