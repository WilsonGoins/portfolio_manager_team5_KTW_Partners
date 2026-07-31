// src/App.jsx
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";

// Each page is its own chunk, so a visit only downloads the one it lands on --
// Overview pulls the data grid, Explore doesn't, and neither waits on the other.
// The pages are named exports, hence the .then that re-labels them as default.
const Overview = lazy(() => import("./pages/Overview").then((m) => ({ default: m.Overview })));
const Explore = lazy(() => import("./pages/Explore").then((m) => ({ default: m.Explore })));
const Analytics = lazy(() => import("./pages/Analytics").then((m) => ({ default: m.Analytics })));
const Transactions = lazy(() => import("./pages/Transactions").then((m) => ({ default: m.Transactions })));
const Details = lazy(() => import("./pages/Details").then((m) => ({ default: m.Details })));

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Layout stays eager so the navbar paints while the page chunk loads,
            and Suspense sits inside it so only the page area is held back. */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Suspense fallback={null}><Overview /></Suspense>} />
          <Route path="explore" element={<Suspense fallback={null}><Explore /></Suspense>} />
          <Route path="analytics" element={<Suspense fallback={null}><Analytics /></Suspense>} />
          <Route path="transactions" element={<Suspense fallback={null}><Transactions /></Suspense>} />
          <Route path="details/:symbol" element={<Suspense fallback={null}><Details /></Suspense>} />

          <Route path="*" element={<h2>404: Page Not Found</h2>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
