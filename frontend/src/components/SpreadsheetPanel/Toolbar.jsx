import { Download, RefreshCw, FileText, ZoomIn, ZoomOut } from 'lucide-react';
import { useSpreadsheet } from '../../contexts/SpreadsheetContext';
import { API_V1 } from '@/config/api';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const Toolbar = ({ zoom, onZoomChange }) => {
    const { currentFile, currentSheet, refreshCurrentSheet, loading } = useSpreadsheet();

    if (!currentFile) return null;

    const handleDownloadExcel = () => {
        window.open(`${API_V1}/spreadsheet/files/${currentFile}/download`, '_blank');
    };

    const handleExportCsv = () => {
        if (currentSheet) {
            window.open(`${API_V1}/spreadsheet/files/${currentFile}/export/csv/${currentSheet}`, '_blank');
        }
    };

    const handleZoomIn = () => {
        const newZoom = Math.min(zoom + 10, 200);
        onZoomChange(newZoom);
    };

    const handleZoomOut = () => {
        const newZoom = Math.max(zoom - 10, 50);
        onZoomChange(newZoom);
    };

    const handleZoomReset = () => {
        onZoomChange(100);
    };

    return (
        <div className="h-14 border-b border-gray-200 bg-white px-4 flex items-center justify-between shadow-sm z-10">
            <div className="flex items-center gap-3">
                <div className="bg-gray-200 p-1.5 rounded-md">
                    <span className="material-symbols-rounded text-gray-700 text-xl">rubric</span>
                </div>
                <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
                        {currentFile}
                    </span>
                    <span className="text-xs text-gray-500">
                        {currentSheet || 'No sheet selected'}
                    </span>
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Zoom Controls */}
                <div className="flex items-center gap-0.5 rounded-full bg-gray-100 p-0.5">
                    <button
                        onClick={handleZoomOut}
                        disabled={zoom <= 50}
                        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Zoom Out"
                    >
                        <ZoomOut className="h-3.5 w-3.5" />
                    </button>
                    <button
                        onClick={handleZoomReset}
                        className="px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200 rounded-full transition-colors min-w-[45px]"
                        title="Reset Zoom"
                    >
                        {zoom}%
                    </button>
                    <button
                        onClick={handleZoomIn}
                        disabled={zoom >= 200}
                        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Zoom In"
                    >
                        <ZoomIn className="h-3.5 w-3.5" />
                    </button>
                </div>

                <button
                    onClick={refreshCurrentSheet}
                    disabled={loading}
                    className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                    title="Refresh Data"
                >
                    <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                </button>

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors">
                            <Download className="h-4 w-4" />
                            Export
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-48">
                        <DropdownMenuItem onClick={handleDownloadExcel} className="cursor-pointer">
                            <FileText className="mr-2 h-4 w-4 text-gray-600" />
                            <span>Download Excel</span>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={handleExportCsv} disabled={!currentSheet} className="cursor-pointer">
                            <span className="material-symbols-rounded mr-2 text-base text-gray-600">rubric</span>
                            <span>Export Sheet as CSV</span>
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>
    );
};

export default Toolbar;
