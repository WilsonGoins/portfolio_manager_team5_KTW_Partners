import React, { useState, useEffect } from "react";
import { TransactionsTable } from "../components/transactions/TransactionsTable";
import "./Transactions.css";

export function Transactions() {
  const [transactionsData, setTransactionsData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchTransactionsData() {
      try {
        setIsLoading(true);
        const response = await fetch('/api/transactions');

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        setTransactionsData(data || []);
      } catch (err) {
        console.error("Failed to fetch transactions data:", err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchTransactionsData();
  }, []);

  return (
    <div className="transactions-page">
      <h2 className="transactions-page-title">Transactions</h2>
      {isLoading ? (
        <div className="card transactions-card">
          <h3>Transactions</h3>
          <p style={{ color: '#718096', padding: '16px' }}>Loading transactions...</p>
        </div>
      ) : error ? (
        <div className="card transactions-card">
          <h3>Transactions</h3>
          <p style={{ color: '#e53e3e', padding: '16px' }}>Error loading data: {error}</p>
        </div>
      ) : transactionsData.length === 0 ? (
        <div className="card transactions-card">
          <h3>Transactions</h3>
          <p style={{ color: '#718096', padding: '16px' }}>No transactions yet. Buy or sell a security to see it show up here.</p>
        </div>
      ) : (
        <TransactionsTable data={transactionsData} />
      )}
    </div>
  );
}
