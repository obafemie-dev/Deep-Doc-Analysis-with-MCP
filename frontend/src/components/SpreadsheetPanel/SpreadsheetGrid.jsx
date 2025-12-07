/**
 * SpreadsheetGrid - Renders the spreadsheet cells using react-spreadsheet
 */
import React, { useMemo } from 'react';
import Spreadsheet from 'react-spreadsheet';
import ChartOverlay from './ChartOverlay';

// Cell dimensions (approximate, used for chart positioning)
const CELL_WIDTH = 100;
const CELL_HEIGHT = 24;
const ROW_HEADER_WIDTH = 50;
const COL_HEADER_HEIGHT = 24;

/**
 * Convert column number to Excel-style letter (1 = A, 26 = Z, 27 = AA, etc.)
 */
function getColumnLabel(colNum) {
  let label = '';
  let num = colNum;

  while (num > 0) {
    const remainder = (num - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    num = Math.floor((num - 1) / 26);
  }

  return label;
}

/**
 * Transform backend cells array to 2D array format for react-spreadsheet
 */
function transformCellsToGrid(cells, dimensions) {
  const { viewport } = dimensions;
  const numRows = viewport.end_row - viewport.start_row + 1;
  const numCols = viewport.end_col - viewport.start_col + 1;

  // Initialize empty grid
  const grid = Array(numRows).fill(null).map(() =>
    Array(numCols).fill(null).map(() => ({ value: '', readOnly: true }))
  );

  // Fill in cell values
  cells.forEach(cell => {
    const rowIdx = cell.row - viewport.start_row;
    const colIdx = cell.col - viewport.start_col;

    if (rowIdx >= 0 && rowIdx < numRows && colIdx >= 0 && colIdx < numCols) {
      const cellData = {
        value: cell.value !== null && cell.value !== undefined ? cell.value : '',
        readOnly: true
      };

      // Apply styles as className
      if (cell.style) {
        const classes = [];
        if (cell.style.bold) classes.push('font-bold');
        if (cell.style.italic) classes.push('italic');
        if (classes.length > 0) {
          cellData.className = classes.join(' ');
        }
      }

      grid[rowIdx][colIdx] = cellData;
    }
  });

  return grid;
}

/**
 * Generate column labels for the viewport
 */
function generateColumnLabels(startCol, endCol) {
  const labels = [];
  for (let col = startCol; col <= endCol; col++) {
    labels.push({ label: getColumnLabel(col) });
  }
  return labels;
}

/**
 * Generate row labels for the viewport
 */
function generateRowLabels(startRow, endRow) {
  const labels = [];
  for (let row = startRow; row <= endRow; row++) {
    labels.push({ label: String(row) });
  }
  return labels;
}

function SpreadsheetGrid({ data }) {
  const { cells, charts, dimensions } = data;
  const { viewport } = dimensions;

  // Transform cells to grid format
  const gridData = useMemo(() =>
    transformCellsToGrid(cells, dimensions),
    [cells, dimensions]
  );

  // Generate labels
  const columnLabels = useMemo(() =>
    generateColumnLabels(viewport.start_col, viewport.end_col),
    [viewport.start_col, viewport.end_col]
  );

  const rowLabels = useMemo(() =>
    generateRowLabels(viewport.start_row, viewport.end_row),
    [viewport.start_row, viewport.end_row]
  );

  return (
    <div className="h-full overflow-auto relative">
      {/* Spreadsheet */}
      <div className="min-w-max">
        <Spreadsheet
          data={gridData}
          columnLabels={columnLabels.map(c => c.label)}
          rowLabels={rowLabels.map(r => r.label)}
          className="spreadsheet-viewer"
        />
      </div>

      {/* Chart overlays */}
      {charts && charts.length > 0 && charts.map(chart => (
        <ChartOverlay
          key={chart.id}
          chart={chart}
          viewport={viewport}
          cellWidth={CELL_WIDTH}
          cellHeight={CELL_HEIGHT}
          rowHeaderWidth={ROW_HEADER_WIDTH}
          colHeaderHeight={COL_HEADER_HEIGHT}
        />
      ))}
    </div>
  );
}

export default SpreadsheetGrid;
