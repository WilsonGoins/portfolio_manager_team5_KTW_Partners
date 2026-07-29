import { Link, NavLink } from "react-router-dom";
import "./Navbar.css";

export function Navbar() {
  return (
    <header className="navbar-container">
      <Link className="navbar-brand" to="/">
        <div className="brand-icon">K</div>
        <span className="brand-name">KTW Partners</span>
      </Link>

      <nav className="navbar-links">
        <NavLink to="/" end>Overview</NavLink>
        <NavLink to="/explore">Explore</NavLink>
        <NavLink to="/transactions">Transactions</NavLink>
      </nav>
    </header>
  );
}
