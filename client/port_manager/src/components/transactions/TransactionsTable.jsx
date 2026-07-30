import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry } from 'ag-grid-community';
import { ClientSideRowModelModule } from 'ag-grid-community';

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import '../overview/Card.css';
import './TransactionsTable.css';

ModuleRegistry.registerModules([ClientSideRowModelModule]);

// Renders "buy" as green/positive and "sell" as red/negative, matching the
// same color convention HoldingsCard uses for day-change.
const ActionCellRenderer = (params) => {
  const val = params.value;
  if (!val) return null;
  const isBuy = val.toLowerCase() === 'buy';
  return (
    <span className={`action-pill ${isBuy ? 'action-buy' : 'action-sell'}`}>
      {val.charAt(0).toUpperCase() + val.slice(1)}
    </span>
  );
};

const dateFormatter = (params) => {
  if (!params.value) return '--';
  const d = new Date(params.value);
  if (isNaN(d.getTime())) return params.value;
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }) + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
};

export function TransactionsTable({ data }) {
  const columnDefs = useMemo(() => [
    {
      // Flask serializes Python datetimes as RFC 1123 strings
      // (e.g. "Tue, 28 Apr 2026 06:30:00 GMT"), which sort alphabetically by
      // month name rather than chronologically. This comparator parses both
      // sides into real Date objects so newest-first sorting works correctly.
      field: 'date',
      headerName: 'Date',
      valueFormatter: dateFormatter,
      comparator: (dateA, dateB) => new Date(dateA) - new Date(dateB),
      cellStyle: { color: '#718096' },
      minWidth: 170,
      flex: 1.4,
      sort: 'desc',
    },
    {
      field: 'ticker',
      headerName: 'Symbol',
      cellStyle: { fontWeight: '600', color: '#1a202c' },
      minWidth: 90,
      flex: 1,
    },
    {
      field: 'action',
      headerName: 'Action',
      cellRenderer: ActionCellRenderer,
      minWidth: 100,
      flex: 1,
    },
    {
      field: 'quantity',
      headerName: 'Shares',
      type: 'numericColumn',
      valueFormatter: (params) =>
        typeof params.value === 'number' ? params.value : '--',
      minWidth: 90,
      flex: 1,
    },
    {
      // price comes from a Postgres DECIMAL column, which Flask's jsonify
      // serializes as a string (e.g. "150.2500") rather than a number, so we
      // parse it before formatting.
      field: 'price',
      headerName: 'Price',
      type: 'numericColumn',
      valueFormatter: (params) => {
        const num = Number(params.value);
        return !isNaN(num) ? `$${num.toFixed(2)}` : '--';
      },
      minWidth: 100,
      flex: 1,
    },
    {
      field: 'total',
      headerName: 'Total',
      type: 'numericColumn',
      valueGetter: (params) => {
        const { quantity, price } = params.data || {};
        const q = Number(quantity);
        const p = Number(price);
        return !isNaN(q) && !isNaN(p) ? q * p : null;
      },
      valueFormatter: (params) =>
        typeof params.value === 'number' ? `$${params.value.toFixed(2)}` : '--',
      minWidth: 110,
      flex: 1.2,
    },
  ], []);

  const defaultColDef = useMemo(() => ({
    resizable: true,
    sortable: true,
    filter: false,
  }), []);

  return (
    <div className="card transactions-card">
      <h3>Transactions</h3>
      <div className="ag-theme-alpine transactions-grid-container">
        <AgGridReact
          rowData={data}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          domLayout="autoHeight"
          rowHeight={44}
          headerHeight={38}
          suppressCellFocus={true}
          pagination={true}
          paginationPageSize={20}
          paginationPageSizeSelector={[10, 20, 50]}
        />
      </div>
    </div>
  );
}
