import { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import Spreadsheet from 'react-spreadsheet';
import { useSpreadsheet } from '../../contexts/SpreadsheetContext';
import ChartOverlay from './ChartOverlay';
import AICursor from './AICursor';
import './spreadsheet-styles.css';

const SpreadsheetGrid = ({ zoom = 100 }) => {
    const { sheetData, loading, error, updateCell, embedCellsInChat, currentSheet, aiCursor } = useSpreadsheet();
    const [columnWidths, setColumnWidths] = useState({});
    const [contextMenu, setContextMenu] = useState(null);
    const [selection, setSelection] = useState(null);
    const containerRef = useRef(null);
    const menuRef = useRef(null);

    // Calculate scale factor from zoom percentage
    const scale = zoom / 100;

    // Close context menu when clicking elsewhere
    useEffect(() => {
        const handleClickOutside = (e) => {
            // Don't close if clicking inside the menu
            if (menuRef.current && menuRef.current.contains(e.target)) {
                return;
            }
            setContextMenu(null);
        };
        
        const handleScroll = () => setContextMenu(null);
        
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('scroll', handleScroll, true);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            document.removeEventListener('scroll', handleScroll, true);
        };
    }, []);

    // Handle selection changes from react-spreadsheet
    // Selection is a class object (RangeSelection, EmptySelection, etc.)
    const handleSelect = useCallback((selected) => {
        if (!selected) {
            setSelection(null);
            return;
        }
        
        // Check if it's a RangeSelection (has range property)
        if (selected.range) {
            const { start, end } = selected.range;
            setSelection({
                start: { row: start.row, col: start.column },
                end: { row: end.row, col: end.column }
            });
        } else if (selected.start !== undefined && selected.end !== undefined) {
            // EntireAxisSelection (rows or columns)
            setSelection({
                start: { row: selected.start, col: 0 },
                end: { row: selected.end, col: 25 }
            });
        } else {
            // EmptySelection or unknown
            setSelection(null);
        }
    }, []);

    // Handle right-click on spreadsheet
    const handleContextMenu = (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        // If no selection from react-spreadsheet, try to detect from click position
        if (!selection) {
            // Get clicked cell from DOM
            const cell = e.target.closest('td.Spreadsheet__cell');
            if (cell) {
                const row = cell.closest('tr');
                const rowIndex = row ? Array.from(row.parentNode.children).indexOf(row) - 1 : -1;
                const cellIndex = Array.from(cell.parentNode.children).indexOf(cell) - 1;
                
                if (rowIndex >= 0 && cellIndex >= 0) {
                    setSelection({
                        start: { row: rowIndex, col: cellIndex },
                        end: { row: rowIndex, col: cellIndex }
                    });
                }
            }
        }

        setContextMenu({ x: e.clientX, y: e.clientY });
    };

    const handleEmbedInChat = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (selection) {
            embedCellsInChat(selection);
        }
        setContextMenu(null);
    };

    const handleCopyReference = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (selection) {
            const label = `${currentSheet}!${getSelectionLabel()}`;
            navigator.clipboard.writeText(label);
        }
        setContextMenu(null);
    };

    const getSelectionLabel = () => {
        if (!selection) return 'selection';
        const { start, end } = selection;
        const startCol = String.fromCharCode(65 + Math.min(start.col, 25));
        const endCol = String.fromCharCode(65 + Math.min(end.col, 25));
        if (start.row === end.row && start.col === end.col) {
            return `${startCol}${start.row + 1}`;
        }
        return `${startCol}${start.row + 1}:${endCol}${end.row + 1}`;
    };

    // Calculate grid dimensions including charts
    const dimensions = useMemo(() => {
        // Always return at least default dimensions
        const defaultRows = 100;
        const defaultCols = 26;

        if (!sheetData) return { rows: defaultRows, cols: defaultCols };

        const { dimensions: dims, charts } = sheetData;
        let maxRow = Math.max(dims.viewport.end_row || 0, defaultRows);
        let maxCol = Math.max(dims.viewport.end_col || 0, defaultCols);

        // Extend for charts
        charts?.forEach(chart => {
            const chartBottom = (chart.anchor.row || 0) + Math.ceil(chart.size.height / 20) + 10;
            const chartRight = (chart.anchor.col || 0) + Math.ceil(chart.size.width / 80) + 5;
            maxRow = Math.max(maxRow, chartBottom);
            maxCol = Math.max(maxCol, chartRight);
        });

        return { rows: maxRow, cols: maxCol };
    }, [sheetData]);

    const { gridData, charts } = useMemo(() => {
        // If no sheetData, return empty grid structure directly
        if (!sheetData) {
            const data = Array(dimensions.rows).fill(null).map(() =>
                Array(dimensions.cols).fill({ value: '', readOnly: false })
            );
            return { gridData: data, charts: [] };
        }

        const { cells, charts, dimensions: dims } = sheetData;
        const startRow = dims.viewport.start_row || 1;
        const startCol = dims.viewport.start_col || 1;

        // Initialize grid
        const data = Array(dimensions.rows).fill(null).map(() =>
            Array(dimensions.cols).fill({ value: '' })
        );

        // Populate cells
        cells.forEach(cell => {
            const rowIdx = cell.row - startRow;
            const colIdx = cell.col - startCol;

            if (rowIdx >= 0 && rowIdx < dimensions.rows && colIdx >= 0 && colIdx < dimensions.cols) {
                data[rowIdx][colIdx] = {
                    value: cell.value,
                    readOnly: false, // Enable editing
                    className: getClassNameFromStyle(cell.style),
                    style: cell.style
                };
            }
        });

        return { gridData: data, charts: charts || [] };
    }, [sheetData, dimensions]);

    // Generate column labels (A, B, C, ...)
    const columnLabels = useMemo(() => {
        return Array.from({ length: dimensions.cols }, (_, i) => {
            let label = '';
            let n = i;
            while (n >= 0) {
                label = String.fromCharCode((n % 26) + 65) + label;
                n = Math.floor(n / 26) - 1;
            }
            return label;
        });
    }, [dimensions.cols]);

    // Handle cell changes
    const handleCellCommit = async (prevCell, nextCell, coords) => {
        // Guard against null cells
        const prevValue = prevCell?.value ?? '';
        const nextValue = nextCell?.value ?? '';
        
        if (prevValue === nextValue) return;

        // Coords are 0-indexed, backend expects 1-indexed
        const row = coords.row + 1;
        const col = coords.column + 1;

        await updateCell(row, col, nextValue);
    };

    if (loading && !sheetData) { // Only show full loading if no data
        return (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                    <span className="text-gray-500 text-sm">Loading spreadsheet data...</span>
                </div>
            </div>
        );
    }

    if (error && !sheetData) {
        return (
            <div className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="text-red-500 font-medium px-4 py-3 bg-red-50 rounded-lg border border-red-100">
                    {error}
                </div>
            </div>
        );
    }

    // if (!sheetData) { ... } removed to support default blank grid

    return (
        <div className="flex-1 overflow-auto relative bg-gray-50">
            <div 
                ref={containerRef}
                className="absolute inset-2 bg-white shadow-sm rounded-sm overflow-auto border border-gray-200 spreadsheet-compact"
                style={{
                    transform: `scale(${scale})`,
                    transformOrigin: 'top left',
                    width: `${100 / scale}%`,
                    height: `${100 / scale}%`
                }}
                onContextMenu={handleContextMenu}
            >
                <Spreadsheet
                    data={gridData}
                    columnLabels={columnLabels}
                    onCellCommit={handleCellCommit}
                    onSelect={handleSelect}
                />

                {/* Render Charts Overlay */}
                {charts.map(chart => (
                    <ChartOverlay 
                        key={chart.id} 
                        chart={chart} 
                        cellWidth={80 * scale} 
                        cellHeight={20 * scale}
                        zoom={zoom}
                    />
                ))}

                {/* AI Cursor Overlay */}
                <AICursor 
                    cursor={aiCursor}
                    cellWidth={80}
                    cellHeight={20}
                    scale={scale}
                />
            </div>

            {/* Context Menu */}
            {contextMenu && (
                <div
                    ref={menuRef}
                    className="fixed bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-[1000] min-w-[200px]"
                    style={{ left: contextMenu.x, top: contextMenu.y }}
                    onMouseDown={(e) => e.stopPropagation()}
                >
                    <button
                        onMouseDown={handleEmbedInChat}
                        disabled={!selection}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span className="material-symbols-rounded text-base text-gray-600">chat</span>
                        <span>Reference in Chat</span>
                        {selection && (
                            <span className="ml-auto text-xs text-gray-400 font-mono bg-gray-100 px-1.5 py-0.5 rounded">
                                {currentSheet}!{getSelectionLabel()}
                            </span>
                        )}
                    </button>
                    <div className="border-t border-gray-100 my-1" />
                    <button
                        onMouseDown={handleCopyReference}
                        disabled={!selection}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span className="material-symbols-rounded text-base text-gray-600">content_copy</span>
                        <span>Copy Reference</span>
                    </button>
                </div>
            )}
        </div>
    );
};

function getClassNameFromStyle(style) {
    if (!style) return '';
    const classes = [];
    if (style.bold) classes.push('font-bold');
    if (style.italic) classes.push('italic');
    return classes.join(' ');
}

export default SpreadsheetGrid;
