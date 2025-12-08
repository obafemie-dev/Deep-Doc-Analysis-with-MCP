import { useState } from 'react';
import { useSpreadsheet } from '../../contexts/SpreadsheetContext';
import Toolbar from './Toolbar';
import SpreadsheetGrid from './SpreadsheetGrid';
import SheetTabs from './SheetTabs';

const SpreadsheetPanel = () => {
    const { currentFile, loadSheets } = useSpreadsheet();
    const [zoom, setZoom] = useState(100);

    // If separate cleanup needed, can do here

    // If separate cleanup needed, can do here

    // Always render main UI structure
    return (
        <div className="h-full flex flex-col bg-white border-l border-gray-200 overflow-hidden relative">
            <Toolbar zoom={zoom} onZoomChange={setZoom} />
            <SpreadsheetGrid zoom={zoom} />
            <SheetTabs />
        </div>
    );
};

export default SpreadsheetPanel;
