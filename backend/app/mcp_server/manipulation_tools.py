"""
Manipulation Tools - Excel CRUD operations and workbook management
"""
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Border, Side, Alignment, PatternFill
import pandas as pd
from typing import Optional, List, Dict, Any, Union
from .utils import (
    load_workbook,
    save_workbook,
    validate_file_path,
    validate_sheet_name,
    get_sheet_names
)


def create_workbook(file_path: str) -> Dict[str, str]:
    """
    Create a new Excel workbook

    Args:
        file_path: Path where workbook will be created

    Returns:
        Success message and file path
    """
    wb = openpyxl.Workbook()
    save_workbook(wb, file_path)

    return {
        'message': 'Workbook created successfully',
        'file_path': file_path,
        'sheets': wb.sheetnames
    }


def create_worksheet(
    file_path: str,
    sheet_name: str,
    index: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add a new worksheet to existing workbook

    Args:
        file_path: Path to Excel file
        sheet_name: Name for new worksheet
        index: Position to insert sheet (default: end)

    Returns:
        Success message with updated sheet list
    """
    wb = load_workbook(file_path)

    if index is not None:
        wb.create_sheet(sheet_name, index)
    else:
        wb.create_sheet(sheet_name)

    save_workbook(wb, file_path)

    return {
        'message': f"Worksheet '{sheet_name}' created successfully",
        'sheets': wb.sheetnames
    }


def get_workbook_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get workbook information including sheets, ranges, and column names

    Args:
        file_path: Path to Excel file

    Returns:
        Workbook metadata with column names from header row
    """
    wb = load_workbook(file_path)

    metadata = {
        'file_path': file_path,
        'sheet_count': len(wb.sheetnames),
        'sheet_names': wb.sheetnames,
        'sheets_info': []
    }

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]

        # Read first row as column headers
        column_names = []
        for col in range(1, ws.max_column + 1):
            cell_value = ws.cell(row=1, column=col).value
            column_names.append(str(cell_value) if cell_value else f"Column{col}")

        metadata['sheets_info'].append({
            'name': sheet_name,
            'max_row': ws.max_row,
            'max_column': ws.max_column,
            'dimensions': ws.dimensions,
            'column_names': column_names
        })

    return metadata


def write_data_to_excel(
    file_path: str,
    data: List[Dict[str, Any]],
    sheet_name: str,
    start_row: int = 1,
    start_col: int = 1,
    include_header: bool = True
) -> Dict[str, str]:
    """
    Write data from list of dictionaries to worksheet

    Args:
        file_path: Path to Excel file
        data: List of dictionaries with data
        sheet_name: Target sheet name
        start_row: Starting row (1-indexed)
        start_col: Starting column (1-indexed)
        include_header: Whether to write column headers

    Returns:
        Success message
    """
    wb = load_workbook(file_path)

    if sheet_name not in wb.sheetnames:
        wb.create_sheet(sheet_name)

    ws = wb[sheet_name]

    # Convert to DataFrame for easier handling
    df = pd.DataFrame(data)

    # Write headers
    if include_header:
        for col_idx, col_name in enumerate(df.columns, start=start_col):
            ws.cell(row=start_row, column=col_idx, value=col_name)
        data_start_row = start_row + 1
    else:
        data_start_row = start_row

    # Write data
    for row_idx, row_data in enumerate(df.values, start=data_start_row):
        for col_idx, value in enumerate(row_data, start=start_col):
            ws.cell(row=row_idx, column=col_idx, value=value)

    save_workbook(wb, file_path)

    return {
        'message': f"Data written to '{sheet_name}' successfully",
        'rows_written': len(data),
        'columns_written': len(df.columns)
    }


def read_data_from_excel(
    file_path: str,
    sheet_name: str,
    range_str: Optional[str] = None,
    include_header: bool = True,
    max_rows: int = 100
) -> Dict[str, Any]:
    """
    Read data from worksheet with smart truncation

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet to read from
        range_str: Optional cell range (e.g., 'A1:C10')
        include_header: Whether first row is header
        max_rows: Maximum number of rows to return (default: 100)

    Returns:
        Data as list of dictionaries (truncated if necessary)
    """
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        header=0 if include_header else None
    )

    # If range specified, filter rows/columns
    if range_str:
        # Simple range parsing (e.g., 'A1:C10')
        # This is a simplified version; production code would need more robust parsing
        pass

    total_rows = len(df)
    is_truncated = total_rows > max_rows

    # If data is too large, return sample from beginning and end
    if is_truncated:
        half = max_rows // 2
        sample_df = pd.concat([df.head(half), df.tail(max_rows - half)])
        data_records = sample_df.to_dict(orient='records')
    else:
        data_records = df.to_dict(orient='records')

    result = {
        'data': data_records,
        'rows': len(data_records),
        'total_rows': total_rows,
        'columns': len(df.columns),
        'column_names': df.columns.tolist() if include_header else None
    }

    if is_truncated:
        result['note'] = f"Dataset truncated: showing {len(data_records)} of {total_rows} rows. Use analyze_excel_data with filters for specific data."
        result['truncated'] = True

    return result


def copy_worksheet(
    file_path: str,
    source_sheet: str,
    target_sheet: str
) -> Dict[str, str]:
    """
    Duplicate a worksheet within the same workbook

    Args:
        file_path: Path to Excel file
        source_sheet: Sheet to copy
        target_sheet: Name for copied sheet

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, source_sheet)

    source_ws = wb[source_sheet]
    target_ws = wb.copy_worksheet(source_ws)
    target_ws.title = target_sheet

    save_workbook(wb, file_path)

    return {
        'message': f"Worksheet '{source_sheet}' copied to '{target_sheet}' successfully",
        'sheets': wb.sheetnames
    }


def delete_worksheet(file_path: str, sheet_name: str) -> Dict[str, str]:
    """
    Remove a worksheet from workbook

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet to delete

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)

    if len(wb.sheetnames) == 1:
        raise ValueError("Cannot delete the only worksheet in workbook")

    del wb[sheet_name]
    save_workbook(wb, file_path)

    return {
        'message': f"Worksheet '{sheet_name}' deleted successfully",
        'remaining_sheets': wb.sheetnames
    }


def rename_worksheet(
    file_path: str,
    old_name: str,
    new_name: str
) -> Dict[str, str]:
    """
    Change a worksheet's name

    Args:
        file_path: Path to Excel file
        old_name: Current sheet name
        new_name: New sheet name

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, old_name)

    ws = wb[old_name]
    ws.title = new_name

    save_workbook(wb, file_path)

    return {
        'message': f"Worksheet renamed from '{old_name}' to '{new_name}' successfully",
        'sheets': wb.sheetnames
    }


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
    """
    Apply formatting to a range of cells

    Args:
        file_path: Path to Excel file
        sheet_name: Target sheet
        range_str: Cell range (e.g., 'A1:C10')
        font_name: Font family name
        font_size: Font size in points
        font_bold: Bold text
        font_color: Font color (hex code)
        bg_color: Background color (hex code)
        border: Apply borders
        alignment: Text alignment ('left', 'center', 'right')

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    # Parse range
    cell_range = ws[range_str]

    # Apply font formatting
    if any([font_name, font_size, font_bold, font_color]):
        font = Font(
            name=font_name,
            size=font_size,
            bold=font_bold,
            color=font_color
        )
        for row in cell_range:
            for cell in (row if isinstance(row, tuple) else [row]):
                cell.font = font

    # Apply background color
    if bg_color:
        fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type='solid')
        for row in cell_range:
            for cell in (row if isinstance(row, tuple) else [row]):
                cell.fill = fill

    # Apply borders
    if border:
        border_style = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        for row in cell_range:
            for cell in (row if isinstance(row, tuple) else [row]):
                cell.border = border_style

    # Apply alignment
    if alignment:
        align = Alignment(horizontal=alignment)
        for row in cell_range:
            for cell in (row if isinstance(row, tuple) else [row]):
                cell.alignment = align

    save_workbook(wb, file_path)

    return {
        'message': f"Formatting applied to range '{range_str}' in sheet '{sheet_name}' successfully"
    }


def apply_formula(
    file_path: str,
    sheet_name: str,
    cell: str,
    formula: str
) -> Dict[str, str]:
    """
    Apply Excel formula to a cell

    Args:
        file_path: Path to Excel file
        sheet_name: Target sheet
        cell: Target cell (e.g., 'A1')
        formula: Excel formula (without '=' prefix)

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    # Ensure formula starts with '='
    if not formula.startswith('='):
        formula = '=' + formula

    ws[cell] = formula
    save_workbook(wb, file_path)

    return {
        'message': f"Formula applied to cell '{cell}' in sheet '{sheet_name}' successfully",
        'formula': formula
    }


def insert_rows(
    file_path: str,
    sheet_name: str,
    row_index: int,
    count: int = 1
) -> Dict[str, str]:
    """
    Insert rows at specified position

    Args:
        file_path: Path to Excel file
        sheet_name: Target sheet
        row_index: Row position to insert at (1-indexed)
        count: Number of rows to insert

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    ws.insert_rows(row_index, count)
    save_workbook(wb, file_path)

    return {
        'message': f"Inserted {count} row(s) at position {row_index} in sheet '{sheet_name}'"
    }


def insert_columns(
    file_path: str,
    sheet_name: str,
    column_index: int,
    count: int = 1
) -> Dict[str, str]:
    """
    Insert columns at specified position

    Args:
        file_path: Path to Excel file
        sheet_name: Target sheet
        column_index: Column position to insert at (1-indexed)
        count: Number of columns to insert

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    ws.insert_cols(column_index, count)
    save_workbook(wb, file_path)

    return {
        'message': f"Inserted {count} column(s) at position {column_index} in sheet '{sheet_name}'"
    }


def delete_rows(
    file_path: str,
    sheet_name: str,
    row_index: int,
    count: int = 1
) -> Dict[str, str]:
    """
    Delete rows from worksheet

    Args:
        file_path: Path to Excel file
        sheet_name: Target sheet
        row_index: Starting row to delete (1-indexed)
        count: Number of rows to delete

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    ws.delete_rows(row_index, count)
    save_workbook(wb, file_path)

    return {
        'message': f"Deleted {count} row(s) starting at position {row_index} in sheet '{sheet_name}'"
    }


def delete_columns(
    file_path: str,
    sheet_name: str,
    column_index: int,
    count: int = 1
) -> Dict[str, str]:
    """
    Delete columns from worksheet

    Args:
        file_path: Path to Excel file
        sheet_name: Target sheet
        column_index: Starting column to delete (1-indexed)
        count: Number of columns to delete

    Returns:
        Success message
    """
    wb = load_workbook(file_path)
    validate_sheet_name(file_path, sheet_name)
    ws = wb[sheet_name]

    ws.delete_cols(column_index, count)
    save_workbook(wb, file_path)

    return {
        'message': f"Deleted {count} column(s) starting at position {column_index} in sheet '{sheet_name}'"
    }
