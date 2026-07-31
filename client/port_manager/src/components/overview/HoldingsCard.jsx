import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry } from 'ag-grid-community';
import { ClientSideRowModelModule } from 'ag-grid-community';
import { formatHoldingType } from '../../utils/holdingType';

import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-alpine.css';
import './HoldingsCard.css';

ModuleRegistry.registerModules([ClientSideRowModelModule]);

// Kept as constants because the container's height is derived from them -- if
// these and the grid's own row sizing drift apart, the table stops cutting off
// cleanly at a row boundary.
const ROW_HEIGHT = 44;
const HEADER_HEIGHT = 38;

// Past this the table scrolls instead of growing, so a long portfolio doesn't
// push the Allocation card far down the page.
const MAX_VISIBLE_ROWS = 10;

export function HoldingsCard({ data }) {

  const navigate = useNavigate();

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

  const handleRowClick = (event) => {
    if(event.data && event.data.symbol) {
      let symbol = event.data.symbol;
      if(symbol !== "--") {
        navigate(`/details/${symbol}`);
      }
    }
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
      valueFormatter: (params) => formatHoldingType(params.value),
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

  // domLayout="autoHeight" would size the grid to every row, so the height is
  // pinned here instead: exactly enough for MAX_VISIBLE_ROWS, and the grid
  // scrolls beyond that. Shorter portfolios still sit snug rather than leaving
  // an empty band under the last row.
  const gridHeight = useMemo(() => {
    const rowCount = Math.min(data?.length ?? 0, MAX_VISIBLE_ROWS);
    return HEADER_HEIGHT + Math.max(rowCount, 1) * ROW_HEIGHT;
  }, [data]);

  return (
    <div className="card holdings-card">
      <h3>Holdings</h3>
      <div className="ag-theme-alpine holdings-grid-container" style={{ height: gridHeight }}>
        <AgGridReact
          rowData={data}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          rowHeight={ROW_HEIGHT}
          headerHeight={HEADER_HEIGHT}
          suppressCellFocus={true}
          onRowClicked={handleRowClick}
        />
      </div>
    </div>
  );
}
