/**
 * SheetTabs - Bottom tab bar for switching between sheets
 */
import React from 'react';

function SheetTabs({ sheets, currentSheet, onSheetSelect }) {
  return (
    <div className="border-t border-gray-200 bg-gray-50 px-2 py-1 flex items-center gap-1 overflow-x-auto">
      {sheets.map(sheet => (
        <button
          key={sheet.name}
          onClick={() => onSheetSelect(sheet.name)}
          className={`
            px-3 py-1.5 text-sm rounded-t-lg transition-colors flex items-center gap-1.5
            ${currentSheet === sheet.name
              ? 'bg-white border border-b-0 border-gray-200 text-gray-900 font-medium -mb-px'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            }
          `}
          title={`${sheet.name} (${sheet.row_count} rows x ${sheet.col_count} cols)`}
        >
          {sheet.has_charts && (
            <svg
              className="w-3.5 h-3.5 text-blue-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          )}
          <span className="max-w-32 truncate">{sheet.name}</span>
        </button>
      ))}

      {/* Show total sheet count if many sheets */}
      {sheets.length > 5 && (
        <span className="text-xs text-gray-400 px-2">
          {sheets.length} sheets
        </span>
      )}
    </div>
  );
}

export default SheetTabs;
