// src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Overview } from "./pages/Overview";
import { Explore } from "./pages/Explore";
import { Transactions } from "./pages/Transactions";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="explore" element={<Explore />} />
          <Route path="transactions" element={<Transactions />} />

          <Route path="*" element={<h2>404: Page Not Found</h2>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
