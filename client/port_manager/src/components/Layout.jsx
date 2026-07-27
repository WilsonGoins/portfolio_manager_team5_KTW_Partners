// src/components/Layout.jsx
import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css"; // optional custom styling
import {Navbar} from "./Navbar"

export function Layout() {
  return (
    <div>
      <Navbar />
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
