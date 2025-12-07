/**
 * SpreadsheetPanel - Main container for the spreadsheet viewer
 */
import React, { useEffect } from 'react';
import { useSpreadsheet } from '@/contexts/SpreadsheetContext';
import Toolbar from './Toolbar';
import SpreadsheetGrid from './SpreadsheetGrid';
import SheetTabs from './SheetTabs';

function SpreadsheetPanel({ filename }) {
  const {
    currentFile,
    sheets,
    currentSheet,
    sheetData,
    loading,
    error,
    loadSheets,
    selectSheet,
    refreshCurrentSheet
  } = useSpreadsheet();

  // Load sheets when filename changes
  useEffect(() => {
    if (filename && filename !== currentFile) {
      loadSheets(filename);
    }
  }, [filename, currentFile, loadSheets]);

  // Empty state - no file uploaded
  if (!filename) {
    return (
      <div className="bg-white rounded-lg shadow-sm h-full flex items-center justify-center border border-gray-100">
        <div className="text-center text-gray-500 p-8">
          <svg
            className="mx-auto h-16 w-16 text-gray-300 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
            />
          </svg>
          <h3 className="text-lg font-medium text-gray-700 mb-2">
            No Spreadsheet
          </h3>
          <p className="text-sm">
            Upload an Excel file to view it here
          </p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm h-full flex items-center justify-center border border-gray-100">
        <div className="text-center text-red-500 p-8">
          <svg
            className="mx-auto h-12 w-12 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <h3 className="text-lg font-medium mb-2">Error Loading Spreadsheet</h3>
          <p className="text-sm mb-4">{error}</p>
          <button
            onClick={refreshCurrentSheet}
            className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm h-full flex flex-col overflow-hidden border border-gray-100 relative">
      {/* Toolbar */}
      <Toolbar filename={filename} />

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-10">
          <div className="flex flex-col items-center">
            <svg
              className="animate-spin h-8 w-8 text-blue-600 mb-2"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="text-sm text-gray-600">Loading...</span>
          </div>
        </div>
      )}

      {/* Grid area */}
      <div className="flex-1 overflow-hidden relative">
        {sheetData ? (
          <SpreadsheetGrid data={sheetData} />
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500">
            {loading ? '' : 'Select a sheet to view'}
          </div>
        )}
      </div>

      {/* Sheet tabs */}
      {sheets.length > 0 && (
        <SheetTabs
          sheets={sheets}
          currentSheet={currentSheet}
          onSheetSelect={selectSheet}
        />
      )}
    </div>
  );
}

export default SpreadsheetPanel;
