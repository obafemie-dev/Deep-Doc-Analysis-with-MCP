import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_V1 } from '@/config/api';

const SpreadsheetContext = createContext(null);

export const SpreadsheetProvider = ({ children }) => {
    const [currentFile, setCurrentFile] = useState(null);
    const [sheets, setSheets] = useState([]);
    const [currentSheet, setCurrentSheet] = useState(null);
    const [sheetData, setSheetData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    
    // Selected cells for embedding in chat
    const [selectedCells, setSelectedCells] = useState(null);
    const [pendingCellReference, setPendingCellReference] = useState(null);
    
    // AI cursor for showing where AI is working
    const [aiCursor, setAiCursor] = useState(null);

    // Load list of sheets for a file
    const loadSheets = useCallback(async (filename, options = { autoSelect: true }) => {
        if (!filename) {
            setCurrentFile(null);
            setSheets([]);
            setCurrentSheet(null);
            setSheetData(null);
            return;
        }

        setLoading(true);
        setError(null);
        setCurrentFile(filename);

        try {
            const response = await axios.get(`${API_V1}/spreadsheet/files/${filename}/sheets`, {
                withCredentials: true
            });
            setSheets(response.data);

            // Auto-select first sheet if requested and none selected
            if (options.autoSelect && response.data.length > 0) {
                setCurrentSheet(response.data[0].name);
            }
        } catch (err) {
            console.error('Error loading sheets:', err);
            setError('Failed to load sheets');
        } finally {
            setLoading(false);
        }
    }, []);

    // Load data for specific sheet
    const loadSheetData = useCallback(async (filename, sheetName) => {
        if (!filename || !sheetName) return;

        setLoading(true);
        setError(null);

        try {
            // Default viewport A1:Z100 implied by backend defaults
            const response = await axios.get(
                `${API_V1}/spreadsheet/files/${filename}/sheet/${sheetName}`,
                { withCredentials: true }
            );
            setSheetData(response.data);
        } catch (err) {
            console.error(`Error loading sheet ${sheetName}:`, err);
            setError(`Failed to load sheet: ${sheetName}`);
        } finally {
            setLoading(false);
        }
    }, []);

    // Reload current sheet (e.g., after manual refresh)
    const refreshCurrentSheet = useCallback(() => {
        setRefreshTrigger(prev => prev + 1);
    }, []);

    // Effect to load sheet data when file, sheet, or refresh trigger changes
    useEffect(() => {
        if (currentFile && currentSheet) {
            loadSheetData(currentFile, currentSheet);
        }
    }, [currentFile, currentSheet, refreshTrigger, loadSheetData]);

    // Handle updates from AI (SSE events)
    const handleSheetUpdate = useCallback(async (updateInfo) => {
        if (!updateInfo.filename) return;

        // Always reload sheets list to catch new sheets created by AI
        await loadSheets(updateInfo.filename, { autoSelect: false });

        // If a specific sheet was modified and it's the current one, make sure we're viewing it
        if (updateInfo.sheet_name) {
            // Switch to the modified sheet if it exists
            setCurrentSheet(updateInfo.sheet_name);
        }
    }, [loadSheets]);

    const clearSpreadsheet = useCallback(() => {
        setCurrentFile(null);
        setSheets([]);
        setCurrentSheet(null);
        setSheetData(null);
        setError(null);
    }, []);

    const updateCell = useCallback(async (row, col, value) => {
        if (!currentFile || !currentSheet) return;

        try {
            await axios.post(
                `${API_V1}/spreadsheet/files/${currentFile}/sheet/${currentSheet}/cell`,
                { row, col, value },
                { withCredentials: true }
            );

            // Optimistic update or refresh could happen here
            // For now, we'll trigger a silent refresh
            setRefreshTrigger(prev => prev + 1);
            return true;
        } catch (err) {
            console.error('Error updating cell:', err);
            setError('Failed to update cell');
            return false;
        }
    }, [currentFile, currentSheet]);

    const createSheet = useCallback(async (sheetName) => {
        if (!currentFile) return false;

        try {
            await axios.post(
                `${API_V1}/spreadsheet/files/${currentFile}/sheets`,
                { sheet_name: sheetName },
                { withCredentials: true }
            );

            // Reload sheets list and switch to new sheet
            await loadSheets(currentFile, { autoSelect: false });
            setCurrentSheet(sheetName);
            return true;
        } catch (err) {
            console.error('Error creating sheet:', err);
            setError(err.response?.data?.detail || 'Failed to create sheet');
            return false;
        }
    }, [currentFile, loadSheets]);

    // Function to embed selected cells into chat
    const embedCellsInChat = useCallback((selection) => {
        if (!selection || !currentSheet) return;
        
        const { start, end } = selection;
        const startCol = String.fromCharCode(65 + start.col);
        const endCol = String.fromCharCode(65 + end.col);
        const range = start.row === end.row && start.col === end.col
            ? `${startCol}${start.row + 1}`
            : `${startCol}${start.row + 1}:${endCol}${end.row + 1}`;
        
        setPendingCellReference({
            sheet: currentSheet,
            range,
            selection
        });
    }, [currentSheet]);

    const clearPendingCellReference = useCallback(() => {
        setPendingCellReference(null);
    }, []);

    const value = {
        currentFile,
        sheets,
        currentSheet,
        setCurrentSheet,
        sheetData,
        loading,
        error,
        updateCell,
        createSheet,
        loadSheets,
        refreshCurrentSheet,
        handleSheetUpdate,
        clearSpreadsheet,
        selectedCells,
        setSelectedCells,
        embedCellsInChat,
        pendingCellReference,
        clearPendingCellReference,
        aiCursor,
        setAiCursor
    };

    return (
        <SpreadsheetContext.Provider value={value}>
            {children}
        </SpreadsheetContext.Provider>
    );
};

export const useSpreadsheet = () => {
    const context = useContext(SpreadsheetContext);
    if (!context) {
        throw new Error('useSpreadsheet must be used within a SpreadsheetProvider');
    }
    return context;
};
