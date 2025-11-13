"""
Pivot Table and Chart Tools - Data visualization and pivot operations
"""
import pandas as pd
import openpyxl
from openpyxl.chart import (
    BarChart,
    LineChart,
    PieChart,
    ScatterChart,
    AreaChart,
    Reference
)
from typing import Optional, List, Dict, Any
from .utils import (
    load_workbook,
    load_dataframe,
    save_workbook,
    validate_sheet_name,
    serialize_dataframe_for_json
)


def create_pivot_table(
    file_path: str,
    source_sheet: str,
    target_sheet: str,
    rows: List[str],
    columns: Optional[List[str]] = None,
    values: str = None,
    aggfunc: str = 'sum'
) -> Dict[str, Any]:
    """
    Create dynamic pivot table for data analysis

    Args:
        file_path: Path to Excel file
        source_sheet: Source data sheet
        target_sheet: Target sheet for pivot table
        rows: Row fields for pivot
        columns: Column fields for pivot (optional)
        values: Value field to aggregate
        aggfunc: Aggregation function ('sum', 'mean', 'count', 'min', 'max')

    Returns:
        Pivot table data and success message
    """
    df = load_dataframe(file_path, source_sheet)

    # Create pivot table
    if columns:
        pivot = pd.pivot_table(
            df,
            index=rows,
            columns=columns,
            values=values,
            aggfunc=aggfunc,
            fill_value=0
        )
    else:
        pivot = df.groupby(rows)[values].agg(aggfunc) if values else df.groupby(rows).size()

    # Save to Excel
    wb = load_workbook(file_path)

    # Create target sheet if it doesn't exist
    if target_sheet in wb.sheetnames:
        del wb[target_sheet]

    # Write pivot table
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a') as writer:
        pivot.to_excel(writer, sheet_name=target_sheet)

    return {
        'message': f"Pivot table created in sheet '{target_sheet}' successfully",
        'pivot_shape': {'rows': pivot.shape[0], 'columns': pivot.shape[1]},
        'preview': serialize_dataframe_for_json(pivot.head(10)) if hasattr(pivot, 'head') else str(pivot)
    }


def analyze_pivot_data(
    file_path: str,
    pivot_sheet: str
) -> Dict[str, Any]:
    """
    Statistical analysis of pivot table results

    Args:
        file_path: Path to Excel file
        pivot_sheet: Sheet containing pivot table

    Returns:
        Analysis results of pivot data
    """
    df = load_dataframe(file_path, pivot_sheet)

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

    analysis = {
        'shape': {'rows': df.shape[0], 'columns': df.shape[1]},
        'summary_statistics': {}
    }

    for col in numeric_cols:
        analysis['summary_statistics'][col] = {
            'sum': float(df[col].sum()),
            'mean': float(df[col].mean()),
            'median': float(df[col].median()),
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            'std': float(df[col].std())
        }

    return analysis


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
    Generate charts from specified data ranges

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet containing data
        chart_type: Type of chart ('line', 'bar', 'pie', 'scatter', 'area')
        data_range: Data range for chart (e.g., 'A1:B10')
        chart_title: Title for chart
        x_axis_title: X-axis label
        y_axis_title: Y-axis label
        position: Cell position for chart (e.g., 'E5')

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    # Parse data range
    data = Reference(ws, range_string=f"{sheet_name}!{data_range}")

    # Create chart based on type
    chart_types = {
        'line': LineChart,
        'bar': BarChart,
        'pie': PieChart,
        'scatter': ScatterChart,
        'area': AreaChart
    }

    if chart_type not in chart_types:
        raise ValueError(f"Invalid chart type. Choose from: {list(chart_types.keys())}")

    chart = chart_types[chart_type]()

    # Configure chart
    if chart_title:
        chart.title = chart_title

    if x_axis_title and hasattr(chart, 'x_axis'):
        chart.x_axis.title = x_axis_title

    if y_axis_title and hasattr(chart, 'y_axis'):
        chart.y_axis.title = y_axis_title

    # Add data
    chart.add_data(data, titles_from_data=True)

    # Add chart to worksheet
    ws.add_chart(chart, position)

    save_workbook(wb, file_path)

    return {
        'message': f"{chart_type.capitalize()} chart created successfully in sheet '{sheet_name}'",
        'chart_type': chart_type,
        'position': position
    }


def create_dashboard(
    file_path: str,
    dashboard_sheet: str,
    charts_config: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Create multi-chart dashboard

    Args:
        file_path: Path to Excel file
        dashboard_sheet: Sheet for dashboard
        charts_config: List of chart configurations, each containing:
            - source_sheet: Sheet with data
            - chart_type: Type of chart
            - data_range: Data range
            - title: Chart title
            - position: Cell position

    Returns:
        Success message
    """
    wb = load_workbook(file_path)

    # Create dashboard sheet if it doesn't exist
    if dashboard_sheet not in wb.sheetnames:
        wb.create_sheet(dashboard_sheet)

    ws = wb[dashboard_sheet]

    # Create each chart
    for config in charts_config:
        source_sheet = config['source_sheet']
        chart_type = config['chart_type']
        data_range = config['data_range']
        position = config.get('position', 'A1')
        title = config.get('title')

        validate_sheet_name(file_path, source_sheet)
        source_ws = wb[source_sheet]

        data = Reference(source_ws, range_string=f"{source_sheet}!{data_range}")

        chart_types = {
            'line': LineChart,
            'bar': BarChart,
            'pie': PieChart,
            'scatter': ScatterChart,
            'area': AreaChart
        }

        if chart_type in chart_types:
            chart = chart_types[chart_type]()
            if title:
                chart.title = title
            chart.add_data(data, titles_from_data=True)
            ws.add_chart(chart, position)

    save_workbook(wb, file_path)

    return {
        'message': f"Dashboard created in sheet '{dashboard_sheet}' with {len(charts_config)} charts",
        'charts_count': len(charts_config)
    }


def create_table(
    file_path: str,
    sheet_name: str,
    data_range: str,
    table_name: str,
    style: str = 'TableStyleMedium2'
) -> Dict[str, str]:
    """
    Create native Excel table from data range

    Args:
        file_path: Path to Excel file
        sheet_name: Target sheet
        data_range: Range to convert to table (e.g., 'A1:D10')
        table_name: Name for the table
        style: Table style name

    Returns:
        Success message
    """
    from openpyxl.worksheet.table import Table, TableStyleInfo

    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    # Create table
    table = Table(displayName=table_name, ref=data_range)

    # Add style
    table_style = TableStyleInfo(
        name=style,
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False
    )
    table.tableStyleInfo = table_style

    # Add table to worksheet
    ws.add_table(table)

    save_workbook(wb, file_path)

    return {
        'message': f"Table '{table_name}' created successfully in sheet '{sheet_name}'",
        'table_name': table_name,
        'range': data_range
    }
