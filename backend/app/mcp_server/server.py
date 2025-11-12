"""
Main MCP Server - Registers all Excel analysis and manipulation tools
"""
from fastmcp import FastMCP
from typing import Optional, List, Dict, Any

# Import all tool modules
from . import analysis_tools
from . import manipulation_tools
from . import pivot_chart_tools

# Create MCP server instance
mcp_server = FastMCP("Excel Analysis Server")


# ============================================================================
# ANALYSIS TOOLS
# ============================================================================

@mcp_server.tool()
def analyze_excel_data(
    file_path: str,
    sheet_name: Optional[str] = None,
    columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Comprehensive statistical analysis of Excel data.
    Returns summary statistics, null counts, data types, and shape.
    """
    return analysis_tools.analyze_excel_data(file_path, sheet_name, columns)


@mcp_server.tool()
def compare_columns(
    file_path: str,
    column1: str,
    column2: str,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Statistical comparison between two columns.
    Returns correlation, t-test results, and descriptive statistics.
    """
    return analysis_tools.compare_columns(file_path, column1, column2, sheet_name)


@mcp_server.tool()
def validate_data(
    file_path: str,
    sheet_name: Optional[str] = None,
    check_duplicates: bool = True,
    check_outliers: bool = True
) -> Dict[str, Any]:
    """
    Data validation - check for nulls, duplicates, and outliers.
    Returns validation results with issues found.
    """
    return analysis_tools.validate_data(
        file_path, sheet_name, check_duplicates, check_outliers
    )


@mcp_server.tool()
def trend_analysis(
    file_path: str,
    time_column: str,
    value_column: str,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Time-series trend analysis with linear regression.
    Returns trend direction, slope, r-squared, and moving averages.
    """
    return analysis_tools.trend_analysis(
        file_path, time_column, value_column, sheet_name
    )


@mcp_server.tool()
def detect_anomalies(
    file_path: str,
    column: str,
    sheet_name: Optional[str] = None,
    method: str = 'zscore',
    threshold: float = 3.0
) -> Dict[str, Any]:
    """
    Detect anomalies/outliers in data using statistical methods.
    Methods: 'zscore' or 'iqr'. Returns anomaly indices and values.
    """
    return analysis_tools.detect_anomalies(
        file_path, column, sheet_name, method, threshold
    )


@mcp_server.tool()
def compare_sheets(
    file_path: str,
    sheet1: str,
    sheet2: str,
    key_column: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare data between two sheets.
    Returns shape comparison, column differences, and row comparisons.
    """
    return analysis_tools.compare_sheets(file_path, sheet1, sheet2, key_column)


# ============================================================================
# MANIPULATION TOOLS
# ============================================================================

@mcp_server.tool()
def create_workbook(file_path: str) -> Dict[str, str]:
    """Create a new Excel workbook at the specified path."""
    return manipulation_tools.create_workbook(file_path)


@mcp_server.tool()
def create_worksheet(
    file_path: str,
    sheet_name: str,
    index: Optional[int] = None
) -> Dict[str, Any]:
    """Add a new worksheet to existing workbook."""
    return manipulation_tools.create_worksheet(file_path, sheet_name, index)


@mcp_server.tool()
def get_workbook_metadata(file_path: str) -> Dict[str, Any]:
    """Get workbook information including sheets and ranges."""
    return manipulation_tools.get_workbook_metadata(file_path)


@mcp_server.tool()
def write_data_to_excel(
    file_path: str,
    data: List[Dict[str, Any]],
    sheet_name: str,
    start_row: int = 1,
    start_col: int = 1,
    include_header: bool = True
) -> Dict[str, str]:
    """Write data from list of dictionaries to worksheet."""
    return manipulation_tools.write_data_to_excel(
        file_path, data, sheet_name, start_row, start_col, include_header
    )


@mcp_server.tool()
def read_data_from_excel(
    file_path: str,
    sheet_name: str,
    range_str: Optional[str] = None,
    include_header: bool = True
) -> Dict[str, Any]:
    """Read data from worksheet. Returns data as list of dictionaries."""
    return manipulation_tools.read_data_from_excel(
        file_path, sheet_name, range_str, include_header
    )


@mcp_server.tool()
def copy_worksheet(
    file_path: str,
    source_sheet: str,
    target_sheet: str
) -> Dict[str, str]:
    """Duplicate a worksheet within the same workbook."""
    return manipulation_tools.copy_worksheet(file_path, source_sheet, target_sheet)


@mcp_server.tool()
def delete_worksheet(file_path: str, sheet_name: str) -> Dict[str, str]:
    """Remove a worksheet from workbook."""
    return manipulation_tools.delete_worksheet(file_path, sheet_name)


@mcp_server.tool()
def rename_worksheet(
    file_path: str,
    old_name: str,
    new_name: str
) -> Dict[str, str]:
    """Change a worksheet's name."""
    return manipulation_tools.rename_worksheet(file_path, old_name, new_name)


@mcp_server.tool()
def format_range(
    file_path: str,
    sheet_name: str,
    range_str: str,
    font_name: Optional[str] = None,
    font_size: Optional[int] = None,
    font_bold: Optional[bool] = None,
    font_color: Optional[str] = None,
    bg_color: Optional[str] = None,
    border: Optional[bool] = None,
    alignment: Optional[str] = None
) -> Dict[str, str]:
    """Apply formatting to a range of cells."""
    return manipulation_tools.format_range(
        file_path, sheet_name, range_str, font_name, font_size,
        font_bold, font_color, bg_color, border, alignment
    )


@mcp_server.tool()
def apply_formula(
    file_path: str,
    sheet_name: str,
    cell: str,
    formula: str
) -> Dict[str, str]:
    """Apply Excel formula to a cell."""
    return manipulation_tools.apply_formula(file_path, sheet_name, cell, formula)


@mcp_server.tool()
def insert_rows(
    file_path: str,
    sheet_name: str,
    row_index: int,
    count: int = 1
) -> Dict[str, str]:
    """Insert rows at specified position."""
    return manipulation_tools.insert_rows(file_path, sheet_name, row_index, count)


@mcp_server.tool()
def insert_columns(
    file_path: str,
    sheet_name: str,
    column_index: int,
    count: int = 1
) -> Dict[str, str]:
    """Insert columns at specified position."""
    return manipulation_tools.insert_columns(file_path, sheet_name, column_index, count)


@mcp_server.tool()
def delete_rows(
    file_path: str,
    sheet_name: str,
    row_index: int,
    count: int = 1
) -> Dict[str, str]:
    """Delete rows from worksheet."""
    return manipulation_tools.delete_rows(file_path, sheet_name, row_index, count)


@mcp_server.tool()
def delete_columns(
    file_path: str,
    sheet_name: str,
    column_index: int,
    count: int = 1
) -> Dict[str, str]:
    """Delete columns from worksheet."""
    return manipulation_tools.delete_columns(file_path, sheet_name, column_index, count)


# ============================================================================
# PIVOT TABLE AND CHART TOOLS
# ============================================================================

@mcp_server.tool()
def create_pivot_table(
    file_path: str,
    source_sheet: str,
    target_sheet: str,
    rows: List[str],
    columns: Optional[List[str]] = None,
    values: Optional[str] = None,
    aggfunc: str = 'sum'
) -> Dict[str, Any]:
    """
    Create dynamic pivot table for data analysis.
    Supports aggregation functions: sum, mean, count, min, max.
    """
    return pivot_chart_tools.create_pivot_table(
        file_path, source_sheet, target_sheet, rows, columns, values, aggfunc
    )


@mcp_server.tool()
def analyze_pivot_data(
    file_path: str,
    pivot_sheet: str
) -> Dict[str, Any]:
    """Statistical analysis of pivot table results."""
    return pivot_chart_tools.analyze_pivot_data(file_path, pivot_sheet)


@mcp_server.tool()
def create_chart(
    file_path: str,
    sheet_name: str,
    chart_type: str,
    data_range: str,
    chart_title: Optional[str] = None,
    x_axis_title: Optional[str] = None,
    y_axis_title: Optional[str] = None,
    position: str = 'E5'
) -> Dict[str, str]:
    """
    Generate charts from data ranges.
    Chart types: line, bar, pie, scatter, area.
    """
    return pivot_chart_tools.create_chart(
        file_path, sheet_name, chart_type, data_range,
        chart_title, x_axis_title, y_axis_title, position
    )


@mcp_server.tool()
def create_dashboard(
    file_path: str,
    dashboard_sheet: str,
    charts_config: List[Dict[str, Any]]
) -> Dict[str, str]:
    """Create multi-chart dashboard with multiple visualizations."""
    return pivot_chart_tools.create_dashboard(file_path, dashboard_sheet, charts_config)


@mcp_server.tool()
def create_table(
    file_path: str,
    sheet_name: str,
    data_range: str,
    table_name: str,
    style: str = 'TableStyleMedium2'
) -> Dict[str, str]:
    """Create native Excel table from data range with styling."""
    return pivot_chart_tools.create_table(
        file_path, sheet_name, data_range, table_name, style
    )
