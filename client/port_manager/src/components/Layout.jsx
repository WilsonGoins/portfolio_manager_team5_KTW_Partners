// src/components/Layout.jsx
import { NavLink, Outlet } from "react-router-dom";
import "./Layout.css"; // optional custom styling
import {Navbar} from "./Navbar"
import { DataFreshnessProvider } from "../context/DataFreshness";

export function Layout() {
  return (
    <DataFreshnessProvider>
      <div>
        <Navbar />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </DataFreshnessProvider>
  );
}
