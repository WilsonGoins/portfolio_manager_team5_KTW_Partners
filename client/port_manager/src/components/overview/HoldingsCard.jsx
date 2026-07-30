import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry } from 'ag-grid-community';
import { ClientSideRowModelModule } from 'ag-grid-community';

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import './HoldingsCard.css';

ModuleRegistry.registerModules([ClientSideRowModelModule]);

export function HoldingsCard({ data }) {
  const ChangeCellRenderer = (params) => {
    const val = params.value;
    if (val === null || val === undefined || val === "--") return "--";
    const isPositive = val >= 0;
    const formatted = `${isPositive ? '+' : ''}${Number(val).toFixed(2)}%`;
    return (
      <span className={isPositive ? 'positive' : 'negative'}>
        {formatted}
      </span>
    );
  };

  const columnDefs = useMemo(() => [
    {
      field: 'symbol',
      headerName: 'Symbol',
      cellStyle: { fontWeight: '600', color: '#1a202c' },
      minWidth: 90,
      flex: 1,
    },
    {
      field: 'name',
      headerName: 'Name',
      cellStyle: { color: '#718096' },
      minWidth: 150,
      flex: 2,
    },
    {
      field: 'h_type',
      headerName: 'Type',
      valueFormatter: (params) => params.value,
      minWidth: 90,
      flex: 1,
    },
    {
      field: 'num_shares',
      headerName: 'Shares',
      type: 'numericColumn',
      valueFormatter: (params) => typeof params.value === 'number' ? params.value : '--',
      minWidth: 80,
      flex: 1,
    },
    {
      field: 'curr_price',
      headerName: 'Price',
      type: 'numericColumn',
      valueFormatter: (params) => typeof params.value === 'number' ? `$${params.value?.toFixed(2)}` : '--',
      minWidth: 100,
      flex: 1,
    },
    {
      field: 'market_value',
      headerName: 'Mkt Value',
      type: 'numericColumn',
      valueFormatter: (params) => typeof params.value === 'number' ? `$${params.value?.toFixed(2)}` : '--',
      minWidth: 110,
      flex: 1.2,
    },
    {
      field: 'change_pct_since_close',
      headerName: 'Day Change',
      type: 'numericColumn',
      cellRenderer: ChangeCellRenderer,
      minWidth: 110,
      flex: 1,
    },
    {
      field: 'allocation_pct',
      headerName: 'Alloc',
      type: 'numericColumn',
      valueFormatter: (params) => 
        typeof params.value === 'number' ? `${params.value.toFixed(1)}%` : '--',
      minWidth: 90,
      flex: 1,
    },
  ], []);

  const defaultColDef = useMemo(() => ({
    resizable: true,
    sortable: true,
    filter: false,
  }), []);

  return (
    <div className="card holdings-card">
      <h3>Holdings</h3>
      <div className="ag-theme-alpine holdings-grid-container">
        <AgGridReact
          rowData={data}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          domLayout="autoHeight"
          rowHeight={44}
          headerHeight={38}
          suppressCellFocus={true}
        />
      </div>
    </div>
  );
}
