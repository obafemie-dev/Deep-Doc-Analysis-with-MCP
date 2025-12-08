import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { X, Maximize2, Minimize2, Move } from 'lucide-react';
import { API_V1 } from '@/config/api';
import { useSpreadsheet } from '../../contexts/SpreadsheetContext';

const ChartOverlay = ({ chart, onClose, cellWidth = 80, cellHeight = 20, zoom = 100 }) => {
    const { currentFile, currentSheet, refreshCurrentSheet } = useSpreadsheet();
    const { id, type, anchor, size, title } = chart;
    const [isExpanded, setIsExpanded] = useState(false);
    const [chartData, setChartData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    
    // Drag state
    const [isDragging, setIsDragging] = useState(false);
    const [position, setPosition] = useState({ left: (anchor.col - 1) * cellWidth, top: (anchor.row - 1) * cellHeight });
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const chartRef = useRef(null);
    
    // Resize state
    const [isResizing, setIsResizing] = useState(false);
    const [chartSize, setChartSize] = useState({ 
        width: Math.min(size.width || 500, 800), 
        height: Math.min(size.height || 350, 600) 
    });
    const [resizeStart, setResizeStart] = useState({ x: 0, y: 0, width: 0, height: 0 });

    // Calculate position
    const left = position.left;
    const top = position.top;

    useEffect(() => {
        const fetchChartData = async () => {
            if (!currentFile || !currentSheet || !id) return;

            setIsLoading(true);
            setError(null);
            try {
                const response = await axios.get(
                    `${API_V1}/spreadsheet/files/${encodeURIComponent(currentFile)}/sheet/${encodeURIComponent(currentSheet)}/chart/${id}/plotly`
                );
                setChartData(response.data);
            } catch (err) {
                console.error("Failed to load chart data:", err);
                setError("Failed to load chart data");
            } finally {
                setIsLoading(false);
            }
        };

        fetchChartData();
    }, [currentFile, currentSheet, id]);

    // Update position when anchor changes
    useEffect(() => {
        setPosition({
            left: (anchor.col - 1) * cellWidth,
            top: (anchor.row - 1) * cellHeight
        });
    }, [anchor.col, anchor.row, cellWidth, cellHeight]);

    // Drag handlers
    const handleMouseDown = (e) => {
        if (isExpanded) return; // Don't allow dragging when expanded
        
        // Only start drag if clicking on header (not buttons)
        if (e.target.closest('button')) return;
        
        setIsDragging(true);
        setDragStart({
            x: e.clientX - position.left,
            y: e.clientY - position.top
        });
        e.preventDefault();
    };

    const handleMouseMove = (e) => {
        if (!isDragging) return;

        const newLeft = e.clientX - dragStart.x;
        const newTop = e.clientY - dragStart.y;

        setPosition({
            left: Math.max(0, newLeft),
            top: Math.max(0, newTop)
        });
    };

    const handleMouseUp = async () => {
        if (!isDragging) return;
        setIsDragging(false);

        // Calculate new cell position
        const newCol = Math.max(1, Math.round(position.left / cellWidth) + 1);
        const newRow = Math.max(1, Math.round(position.top / cellHeight) + 1);

        // Only update if position changed
        if (newCol !== anchor.col || newRow !== anchor.row) {
            try {
                await axios.patch(
                    `${API_V1}/spreadsheet/files/${encodeURIComponent(currentFile)}/sheet/${encodeURIComponent(currentSheet)}/chart/${id}/position`,
                    {
                        row: newRow,
                        col: newCol
                    },
                    { withCredentials: true }
                );
                
                // Refresh the sheet to get updated chart positions
                refreshCurrentSheet();
            } catch (err) {
                console.error("Failed to update chart position:", err);
                // Revert to original position on error
                setPosition({
                    left: (anchor.col - 1) * cellWidth,
                    top: (anchor.row - 1) * cellHeight
                });
            }
        }
    };

    // Add global mouse listeners for drag
    useEffect(() => {
        if (isDragging) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            return () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }, [isDragging, position, dragStart]);

    // Resize handlers
    const handleResizeMouseDown = (e) => {
        if (isExpanded) return;
        e.preventDefault();
        e.stopPropagation();
        setIsResizing(true);
        setResizeStart({
            x: e.clientX,
            y: e.clientY,
            width: chartSize.width,
            height: chartSize.height
        });
    };

    const handleResizeMouseMove = (e) => {
        if (!isResizing) return;
        
        const deltaX = e.clientX - resizeStart.x;
        const deltaY = e.clientY - resizeStart.y;
        
        const newWidth = Math.max(300, Math.min(1200, resizeStart.width + deltaX));
        const newHeight = Math.max(200, Math.min(800, resizeStart.height + deltaY));
        
        setChartSize({ width: newWidth, height: newHeight });
    };

    const handleResizeMouseUp = () => {
        setIsResizing(false);
    };

    // Add global mouse listeners for resize
    useEffect(() => {
        if (isResizing) {
            document.addEventListener('mousemove', handleResizeMouseMove);
            document.addEventListener('mouseup', handleResizeMouseUp);
            return () => {
                document.removeEventListener('mousemove', handleResizeMouseMove);
                document.removeEventListener('mouseup', handleResizeMouseUp);
            };
        }
    }, [isResizing, resizeStart]);

    return (
        <div
            ref={chartRef}
            className={`absolute bg-white border border-gray-300 flex flex-col z-20 overflow-hidden ${isExpanded ? 'fixed inset-4 z-50 shadow-2xl rounded-lg' : 'shadow-sm rounded-lg'} ${isDragging ? 'cursor-move shadow-xl' : ''} ${isResizing ? 'shadow-xl' : ''}`}
            style={isExpanded ? {} : {
                left: `${left}px`,
                top: `${top}px`,
                width: `${chartSize.width}px`,
                height: `${chartSize.height}px`,
                minWidth: '300px',
                minHeight: '200px',
                transition: (isDragging || isResizing) ? 'none' : 'box-shadow 0.2s'
            }}
        >
            {/* Header - Excel Style (Dark Slate) */}
            <div 
                className={`flex items-center justify-between px-3 py-1.5 bg-slate-700 text-white select-none ${!isExpanded ? 'cursor-move' : ''}`}
                onMouseDown={handleMouseDown}
            >
                <div className="flex items-center gap-2 overflow-hidden">
                    {!isExpanded && (
                        <Move className="h-3.5 w-3.5 opacity-70" />
                    )}
                    <span className="font-semibold text-xs uppercase tracking-wide opacity-90 truncate">
                        {title || 'Chart'}
                    </span>
                </div>
                <div className="flex items-center gap-1 ml-2">
                    <button
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="p-1 text-slate-300 hover:text-white hover:bg-slate-600 rounded transition-colors"
                        title={isExpanded ? 'Minimize' : 'Maximize'}
                    >
                        {isExpanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
                    </button>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="p-1 text-slate-300 hover:text-white hover:bg-slate-600 rounded transition-colors"
                        >
                            <X className="h-3.5 w-3.5" />
                        </button>
                    )}
                </div>
            </div>

            {/* Chart Content */}
            <div className="flex-1 bg-white relative">
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                        <div className="flex flex-col items-center gap-2">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-slate-600"></div>
                            <span className="text-xs text-gray-500">Loading...</span>
                        </div>
                    </div>
                )}

                {error ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-2 p-4">
                        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <span className="text-xs text-center">{error}</span>
                    </div>
                ) : chartData ? (
                    <div className="w-full h-full p-2">
                        <Plot
                            data={chartData.data}
                            layout={{
                                ...chartData.layout,
                                autosize: true,
                                width: undefined,
                                height: undefined,
                                margin: { l: 50, r: 30, t: 40, b: 50 },
                                showlegend: true,
                                legend: { orientation: "h", y: 1.1, x: 0 },
                                paper_bgcolor: 'rgba(0,0,0,0)',
                                plot_bgcolor: 'rgba(0,0,0,0)',
                                font: { family: 'Space Grotesk, sans-serif', size: 11 }
                            }}
                            useResizeHandler={true}
                            style={{ width: '100%', height: '100%' }}
                            config={{
                                responsive: true,
                                displayModeBar: true,
                                displaylogo: false,
                                modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d']
                            }}
                        />
                    </div>
                ) : null}
                
                {/* Resize Handle */}
                {!isExpanded && (
                    <div
                        className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize group"
                        onMouseDown={handleResizeMouseDown}
                    >
                        <svg 
                            className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors"
                            viewBox="0 0 24 24" 
                            fill="currentColor"
                        >
                            <path d="M22 22H20V20H22V22ZM22 18H20V16H22V18ZM18 22H16V20H18V22ZM22 14H20V12H22V14ZM18 18H16V16H18V18ZM14 22H12V20H14V22ZM18 14H16V12H18V14ZM14 18H12V16H14V18ZM14 14H12V12H14V14Z" />
                        </svg>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ChartOverlay;
