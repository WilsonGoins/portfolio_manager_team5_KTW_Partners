import { NavLink } from "react-router-dom";
import "./Navbar.css";

export function Navbar() {
  return (
    <header className="navbar-container">
      <div className="navbar-brand">
        <div className="brand-icon">K</div>
        <span className="brand-name">KTW Partners</span>
      </div>

      <nav className="navbar-links">
        <NavLink to="/" end>Overview</NavLink>
        <NavLink to="/holdings">Holdings</NavLink>
        <NavLink to="/transactions">Transactions</NavLink>
        <NavLink to="/explore">Explore</NavLink>
      </nav>
    </header>
  );
}
