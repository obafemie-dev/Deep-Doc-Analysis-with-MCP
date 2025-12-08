import { useRef, useEffect, useState } from 'react';
import { useSpreadsheet } from '../../contexts/SpreadsheetContext';
import { BarChart, Plus, X } from 'lucide-react';

const SheetTabs = () => {
    const { sheets, currentSheet, setCurrentSheet, createSheet, currentFile } = useSpreadsheet();
    const tabsRef = useRef(null);
    const [isCreating, setIsCreating] = useState(false);
    const [newSheetName, setNewSheetName] = useState('');
    const inputRef = useRef(null);

    // Scroll active tab into view
    useEffect(() => {
        if (currentSheet && tabsRef.current) {
            const activeTab = tabsRef.current.querySelector('[data-active="true"]');
            if (activeTab) {
                activeTab.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
            }
        }
    }, [currentSheet]);

    // Focus input when creating
    useEffect(() => {
        if (isCreating && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isCreating]);

    const handleCreateSheet = async () => {
        if (!newSheetName.trim()) return;
        
        const success = await createSheet(newSheetName.trim());
        if (success) {
            setNewSheetName('');
            setIsCreating(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleCreateSheet();
        } else if (e.key === 'Escape') {
            setIsCreating(false);
            setNewSheetName('');
        }
    };

    // If no sheets, show a default "Sheet1"
    const displaySheets = (sheets && sheets.length > 0) ? sheets : [{ name: 'Sheet1', has_charts: false }];
    const activeSheetName = currentSheet || 'Sheet1';

    return (
        <div className="h-10 bg-gray-100 border-t border-gray-300 flex items-center px-1 gap-1 overflow-x-auto no-scrollbar relative z-10">
            <div className="flex items-center space-x-1 p-1 h-full max-w-full overflow-x-auto" ref={tabsRef}>
                {displaySheets.map((sheet) => (
                    <button
                        key={sheet.name}
                        onClick={() => setCurrentSheet(sheet.name)}
                        data-active={activeSheetName === sheet.name}
                        className={`
              flex items-center gap-2 px-4 py-1.5 text-xs font-medium rounded-t-sm transition-colors whitespace-nowrap h-[calc(100%-4px)] mt-1
              ${activeSheetName === sheet.name
                                ? 'bg-white text-gray-700 border-t-2 border-gray-600 shadow-sm'
                                : 'bg-gray-200 text-gray-600 hover:bg-gray-300 border-transparent'}
            `}
                    >
                        {sheet.has_charts && (
                            <BarChart className="h-3 w-3 opacity-60" />
                        )}
                        <span>{sheet.name}</span>
                    </button>
                ))}

                {/* New sheet input */}
                {isCreating ? (
                    <div className="flex items-center gap-1 ml-1">
                        <input
                            ref={inputRef}
                            type="text"
                            value={newSheetName}
                            onChange={(e) => setNewSheetName(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onBlur={() => {
                                if (!newSheetName.trim()) {
                                    setIsCreating(false);
                                }
                            }}
                            placeholder="Sheet name"
                            className="h-6 w-24 px-2 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-gray-400"
                        />
                        <button
                            onClick={handleCreateSheet}
                            disabled={!newSheetName.trim()}
                            className="flex items-center justify-center h-6 w-6 rounded bg-gray-600 text-white hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            title="Create Sheet"
                        >
                            <Plus className="h-3 w-3" />
                        </button>
                        <button
                            onClick={() => {
                                setIsCreating(false);
                                setNewSheetName('');
                            }}
                            className="flex items-center justify-center h-6 w-6 rounded hover:bg-gray-300 text-gray-500 transition-colors"
                            title="Cancel"
                        >
                            <X className="h-3 w-3" />
                        </button>
                    </div>
                ) : (
                    <button
                        onClick={() => currentFile && setIsCreating(true)}
                        disabled={!currentFile}
                        className="flex items-center justify-center h-6 w-6 rounded hover:bg-gray-300 text-gray-500 transition-colors ml-1 disabled:opacity-50 disabled:cursor-not-allowed"
                        title={currentFile ? "New Sheet" : "Upload a file first"}
                    >
                        <Plus className="h-4 w-4" />
                    </button>
                )}
            </div>
        </div>
    );
};

export default SheetTabs;
