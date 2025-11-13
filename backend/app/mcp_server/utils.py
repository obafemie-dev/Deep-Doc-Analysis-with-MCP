import os
import json
import ast
import logging
import openpyxl
import pandas as pd
from datetime import datetime
from typing import Optional, List, Union, Any, Dict

logger = logging.getLogger(__name__)


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
    # If sheet_name is None, read first sheet (pd.read_excel returns dict if sheet_name=None)
    if sheet_name is None:
        sheet_name = 0  # Read first sheet by index
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


def coerce_string_to_type(value: Any) -> Any:
    """
    Coerce string parameters to proper Python types (dict/list).

    This handles cases where API clients send "{'key': 'value'}" as a string
    instead of an actual dict object.

    Args:
        value: Input value that may be a string representation of dict/list

    Returns:
        Properly typed value (dict, list, or original value)

    Examples:
        >>> coerce_string_to_type("{'Model': '4430'}")
        {'Model': '4430'}
        >>> coerce_string_to_type("['Model', 'VIN']")
        ['Model', 'VIN']
        >>> coerce_string_to_type("simple_string")
        'simple_string'
    """
    if not isinstance(value, str) or not value.strip():
        return value

    # Check if string looks like dict or list
    stripped = value.strip()
    if not ((stripped.startswith('{') and stripped.endswith('}')) or
            (stripped.startswith('[') and stripped.endswith(']'))):
        return value

    # Try ast.literal_eval first (safer)
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        # Fallback to json.loads
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # If both fail, return original value
            logger.warning(f"Failed to coerce string to type: {value[:100]}...")
            return value


def serialize_dataframe_for_json(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert DataFrame to JSON-serializable list of dictionaries.
    Handles datetime objects by converting them to ISO format strings.

    Args:
        df: DataFrame to serialize

    Returns:
        List of dictionaries with datetime objects converted to strings
    """
    # Convert datetime columns to ISO format strings
    df_copy = df.copy()

    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            # Handle datetime64 dtype columns
            df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        elif df_copy[col].dtype == 'object':
            # Check if first non-null value is a datetime-like object
            sample = df_copy[col].dropna().head(1)
            if len(sample) > 0 and isinstance(sample.iloc[0], (pd.Timestamp, datetime)):
                # Convert Timestamp/datetime objects to strings
                df_copy[col] = df_copy[col].apply(
                    lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) and isinstance(x, (pd.Timestamp, datetime)) else x
                )

    return df_copy.to_dict(orient='records')
