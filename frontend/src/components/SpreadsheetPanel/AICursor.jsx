import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AICursor = ({ cursor, cellWidth = 80, cellHeight = 20, scale = 1 }) => {
    const [isVisible, setIsVisible] = useState(false);
    
    useEffect(() => {
        if (cursor) {
            setIsVisible(true);
            // Hide cursor after animation completes
            const timer = setTimeout(() => {
                setIsVisible(false);
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [cursor]);

    if (!cursor || !isVisible) return null;

    const { row, col, end_row, end_col, type, tool_name } = cursor;
    
    // Calculate position
    const isRange = end_row !== undefined && end_col !== undefined;
    const isScan = type === 'scan';
    
    // For scan type, show a full-width indicator
    if (isScan) {
        return (
            <AnimatePresence>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 pointer-events-none z-50"
                    style={{
                        background: 'linear-gradient(180deg, rgba(99, 102, 241, 0.1) 0%, rgba(99, 102, 241, 0) 100%)',
                    }}
                >
                    <motion.div
                        initial={{ y: 0 }}
                        animate={{ y: '100%' }}
                        transition={{ duration: 1.5, ease: 'easeInOut' }}
                        className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500"
                        style={{ boxShadow: '0 0 20px rgba(99, 102, 241, 0.5)' }}
                    />
                    <div className="absolute top-4 left-4 flex items-center gap-2 bg-indigo-500 text-white px-3 py-1.5 rounded-full text-xs font-medium shadow-lg">
                        <motion.span
                            animate={{ opacity: [1, 0.5, 1] }}
                            transition={{ duration: 1, repeat: Infinity }}
                            className="material-symbols-rounded text-sm"
                        >
                            smart_toy
                        </motion.span>
                        <span>AI scanning sheet...</span>
                    </div>
                </motion.div>
            </AnimatePresence>
        );
    }

    // Calculate position for cell/range cursor
    if (row === undefined || col === undefined) return null;
    
    const left = (col + 1) * cellWidth; // +1 for row header
    const top = (row + 1) * cellHeight; // +1 for column header
    const width = isRange ? ((end_col - col + 1) * cellWidth) : cellWidth;
    const height = isRange ? ((end_row - row + 1) * cellHeight) : cellHeight;

    // Get friendly tool name
    const getToolLabel = (name) => {
        const labels = {
            'read_cell': 'Reading',
            'write_cell': 'Writing',
            'read_range': 'Reading range',
            'write_range': 'Writing range',
            'apply_formula': 'Applying formula',
            'format_range': 'Formatting',
            'create_chart': 'Creating chart',
            'create_pivot_table': 'Creating pivot',
            'analyze_excel_data': 'Analyzing'
        };
        return labels[name] || 'Working';
    };

    return (
        <AnimatePresence>
            <motion.div
                key={`${row}-${col}-${Date.now()}`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
                className="absolute pointer-events-none z-50"
                style={{
                    left: left * scale,
                    top: top * scale,
                    width: width * scale,
                    height: height * scale,
                }}
            >
                {/* Cursor highlight */}
                <motion.div
                    animate={{ 
                        boxShadow: [
                            '0 0 0 2px rgba(99, 102, 241, 0.8), 0 0 20px rgba(99, 102, 241, 0.4)',
                            '0 0 0 3px rgba(99, 102, 241, 0.6), 0 0 30px rgba(99, 102, 241, 0.3)',
                            '0 0 0 2px rgba(99, 102, 241, 0.8), 0 0 20px rgba(99, 102, 241, 0.4)'
                        ]
                    }}
                    transition={{ duration: 1, repeat: Infinity }}
                    className="absolute inset-0 rounded-sm bg-indigo-500/10 border-2 border-indigo-500"
                />
                
                {/* AI indicator badge */}
                <motion.div
                    initial={{ y: -10, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.1 }}
                    className="absolute -top-7 left-0 flex items-center gap-1.5 bg-indigo-500 text-white px-2 py-1 rounded-full text-xs font-medium shadow-lg whitespace-nowrap"
                >
                    <motion.span
                        animate={{ rotate: [0, 360] }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                        className="material-symbols-rounded text-xs"
                    >
                        auto_awesome
                    </motion.span>
                    <span>{getToolLabel(tool_name)}</span>
                </motion.div>
                
                {/* Ripple effect */}
                <motion.div
                    initial={{ scale: 1, opacity: 0.5 }}
                    animate={{ scale: 1.5, opacity: 0 }}
                    transition={{ duration: 0.8, repeat: 2 }}
                    className="absolute inset-0 rounded-sm border-2 border-indigo-400"
                />
            </motion.div>
        </AnimatePresence>
    );
};

export default AICursor;

