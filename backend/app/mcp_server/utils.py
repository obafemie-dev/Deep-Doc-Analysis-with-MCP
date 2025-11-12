import os
import openpyxl
import pandas as pd
from typing import Optional, List, Union


def validate_file_path(file_path: str) -> bool:
    """Validate that the file exists and is an Excel file"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.xlsx', '.xls', '.xlsm']:
        raise ValueError(f"Invalid file type: {ext}. Must be .xlsx, .xls, or .xlsm")

    return True


def load_workbook(file_path: str):
    """Load an Excel workbook"""
    validate_file_path(file_path)
    return openpyxl.load_workbook(file_path)


def load_dataframe(file_path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """Load Excel data as pandas DataFrame"""
    validate_file_path(file_path)
    return pd.read_excel(file_path, sheet_name=sheet_name)


def get_sheet_names(file_path: str) -> List[str]:
    """Get all sheet names from workbook"""
    wb = load_workbook(file_path)
    return wb.sheetnames


def validate_sheet_name(file_path: str, sheet_name: str) -> bool:
    """Validate that sheet exists in workbook"""
    sheets = get_sheet_names(file_path)
    if sheet_name not in sheets:
        raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {sheets}")
    return True


def save_workbook(wb, file_path: str):
    """Save workbook to file"""
    wb.save(file_path)
    return True


def format_json_response(data: Union[dict, pd.DataFrame, pd.Series]) -> dict:
    """Format response data as JSON-serializable dict"""
    if isinstance(data, pd.DataFrame):
        return data.to_dict(orient='records')
    elif isinstance(data, pd.Series):
        return data.to_dict()
    return data
