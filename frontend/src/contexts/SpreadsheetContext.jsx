/**
 * Spreadsheet Context for managing spreadsheet viewer state
 *
 * Manages the current file, sheets, and sheet data for the spreadsheet viewer.
 */
import React, { createContext, useState, useContext, useCallback } from 'react';
import { API_V1 } from '@/config/api';

const SpreadsheetContext = createContext(null);

export const SpreadsheetProvider = ({ children }) => {
  const [currentFile, setCurrentFile] = useState(null);
  const [sheets, setSheets] = useState([]);
  const [currentSheet, setCurrentSheet] = useState(null);
  const [sheetData, setSheetData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Load sheets list for a file
   */
  const loadSheets = useCallback(async (filename) => {
    if (!filename) {
      setSheets([]);
      setCurrentSheet(null);
      setSheetData(null);
      setCurrentFile(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_V1}/spreadsheet/files/${encodeURIComponent(filename)}/sheets`);

      if (!response.ok) {
        throw new Error(`Failed to load sheets: ${response.statusText}`);
      }

      const data = await response.json();
      setSheets(data.sheets);
      setCurrentFile(filename);

      // Auto-select first sheet
      if (data.sheets.length > 0) {
        const firstSheet = data.sheets[0].name;
        setCurrentSheet(firstSheet);
        await loadSheetData(filename, firstSheet);
      }
    } catch (err) {
      console.error('Error loading sheets:', err);
      setError(err.message);
      setSheets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Load data for a specific sheet
   */
  const loadSheetData = useCallback(async (filename, sheetName, options = {}) => {
    if (!filename || !sheetName) return;

    const {
      startRow = 1,
      endRow = 100,
      startCol = 1,
      endCol = 26
    } = options;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        start_row: startRow.toString(),
        end_row: endRow.toString(),
        start_col: startCol.toString(),
        end_col: endCol.toString()
      });

      const response = await fetch(
        `${API_V1}/spreadsheet/files/${encodeURIComponent(filename)}/sheet/${encodeURIComponent(sheetName)}?${params}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load sheet data: ${response.statusText}`);
      }

      const data = await response.json();
      setSheetData(data);
      setCurrentSheet(sheetName);
    } catch (err) {
      console.error('Error loading sheet data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Refresh current sheet data
   */
  const refreshCurrentSheet = useCallback(async () => {
    if (currentFile && currentSheet) {
      await loadSheetData(currentFile, currentSheet);
    }
  }, [currentFile, currentSheet, loadSheetData]);

  /**
   * Handle sheet update event from AI
   */
  const handleSheetUpdate = useCallback(async (updateInfo) => {
    console.log('Sheet update received:', updateInfo);

    // If the update is for the current file, refresh
    if (updateInfo.filename === currentFile) {
      // Small delay to ensure file is written
      setTimeout(async () => {
        // Reload sheets list in case new sheets were added
        await loadSheets(currentFile);
      }, 500);
    }
  }, [currentFile, loadSheets]);

  /**
   * Clear spreadsheet state
   */
  const clearSpreadsheet = useCallback(() => {
    setCurrentFile(null);
    setSheets([]);
    setCurrentSheet(null);
    setSheetData(null);
    setError(null);
  }, []);

  /**
   * Select a different sheet
   */
  const selectSheet = useCallback(async (sheetName) => {
    if (currentFile && sheetName !== currentSheet) {
      await loadSheetData(currentFile, sheetName);
    }
  }, [currentFile, currentSheet, loadSheetData]);

  const value = {
    currentFile,
    sheets,
    currentSheet,
    sheetData,
    loading,
    error,
    loadSheets,
    loadSheetData,
    refreshCurrentSheet,
    handleSheetUpdate,
    clearSpreadsheet,
    selectSheet
  };

  return (
    <SpreadsheetContext.Provider value={value}>
      {children}
    </SpreadsheetContext.Provider>
  );
};

/**
 * Hook to use spreadsheet context
 */
export const useSpreadsheet = () => {
  const context = useContext(SpreadsheetContext);

  if (!context) {
    throw new Error('useSpreadsheet must be used within SpreadsheetProvider');
  }

  return context;
};

export default SpreadsheetContext;
