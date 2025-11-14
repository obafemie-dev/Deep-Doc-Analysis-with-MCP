"""
Analysis Tools - Data analysis and statistical operations
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Optional, List, Dict, Any
from .utils import load_dataframe, validate_file_path, validate_sheet_name, coerce_string_to_type, serialize_dataframe_for_json


def query_excel_data(
    file_path: str,
    sheet_name: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    columns: Optional[List[str]] = None,
    max_rows: int = 100
) -> Dict[str, Any]:
    """
    Query Excel data with filtering - returns actual data rows from FULL dataset

    IMPORTANT: This queries the COMPLETE dataset, unlike read_data_from_excel which truncates.
    Use this for ANY query about specific data values.

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet to query (default: first sheet)
        filters: Dictionary of column filters e.g., {'Model': '4430', 'Year': 2023}
        columns: Specific columns to return (default: all columns)
        max_rows: Maximum rows to return (default: 100)

    Returns:
        Dictionary with matching rows, total matches, and column info

    Examples:
        query_excel_data(file, 'Sheet1', filters={'Model': '4430'})
        query_excel_data(file, 'Sheet1', filters={'Year': 2023, 'Status': 'Active'})
    """
    # Defensive parameter parsing using shared utility
    filters = coerce_string_to_type(filters)
    columns = coerce_string_to_type(columns)

    # Validate coerced types
    if filters is not None and not isinstance(filters, dict):
        raise ValueError(f"Invalid filters format. Expected dict, got {type(filters).__name__}: {filters}")

    if columns is not None and not isinstance(columns, list):
        raise ValueError(f"Invalid columns format. Expected list, got {type(columns).__name__}: {columns}")

    df = load_dataframe(file_path, sheet_name)

    # Apply filters if provided
    if filters:
        for col, value in filters.items():
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found. Available: {df.columns.tolist()}")

            # Handle different data types
            if isinstance(value, str):
                # Case-insensitive partial match for strings
                df = df[df[col].astype(str).str.contains(value, case=False, na=False)]
            elif isinstance(value, (list, tuple)):
                # Multiple values - use partial matching for each value (OR condition)
                # This allows ['4430', '4440'] to match '4430G', '4440J', etc.
                import pandas as pd
                mask = pd.Series([False] * len(df))
                for v in value:
                    if isinstance(v, str):
                        # Partial match for strings in list
                        mask |= df[col].astype(str).str.contains(str(v), case=False, na=False)
                    else:
                        # Exact match for numbers in list
                        mask |= (df[col] == v)
                df = df[mask]
            else:
                # Exact match for single numeric value
                df = df[df[col] == value]

    # Select specific columns if requested
    if columns:
        missing_cols = [c for c in columns if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Columns not found: {missing_cols}. Available: {df.columns.tolist()}")
        df = df[columns]

    total_matches = len(df)
    is_truncated = total_matches > max_rows

    # Return sample if too many results
    if is_truncated:
        result_df = df.head(max_rows)
    else:
        result_df = df

    result = {
        'data': serialize_dataframe_for_json(result_df),
        'rows_returned': len(result_df),
        'total_matches': total_matches,
        'columns': df.columns.tolist(),
        'filters_applied': filters or {}
    }

    if is_truncated:
        result['note'] = f"Showing first {max_rows} of {total_matches} matching rows"
        result['truncated'] = True

    return result


def analyze_excel_data(
    file_path: str,
    sheet_name: Optional[str] = None,
    columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Comprehensive statistical analysis of Excel data

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet to analyze (default: first sheet)
        columns: Specific columns to analyze (default: all numeric columns)

    Returns:
        Dictionary with summary statistics, null counts, data types, and shape
    """
    df = load_dataframe(file_path, sheet_name)

    if columns:
        df = df[columns]

    # Get numeric columns for statistical analysis
    numeric_df = df.select_dtypes(include=[np.number])

    # Prevent "Cannot describe a DataFrame without columns" error
    if len(numeric_df.columns) == 0:
        # No numeric columns - return informative response
        return {
            'message': 'No numeric columns found in the selected data',
            'available_columns': df.columns.tolist(),
            'data_types': df.dtypes.astype(str).to_dict(),
            'shape': {'rows': df.shape[0], 'columns': df.shape[1]},
            'suggestion': 'This dataset contains only text/categorical data. Try using query_excel_data() to retrieve specific rows instead of analyze_excel_data().'
        }

    analysis = {
        'summary_statistics': numeric_df.describe().to_dict(),
        'null_counts': df.isnull().sum().to_dict(),
        'null_percentages': (df.isnull().sum() / len(df) * 100).to_dict(),
        'data_types': df.dtypes.astype(str).to_dict(),
        'shape': {'rows': df.shape[0], 'columns': df.shape[1]},
        'column_names': df.columns.tolist(),
        'numeric_columns': numeric_df.columns.tolist()
    }

    return analysis


def compare_columns(
    file_path: str,
    column1: str,
    column2: str,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Statistical comparison between two columns

    Args:
        file_path: Path to Excel file
        column1: First column name
        column2: Second column name
        sheet_name: Sheet name (default: first sheet)

    Returns:
        Correlation, t-test results, and basic statistics
    """
    df = load_dataframe(file_path, sheet_name)

    if column1 not in df.columns or column2 not in df.columns:
        raise ValueError(f"Columns not found. Available: {df.columns.tolist()}")

    col1_data = pd.to_numeric(df[column1], errors='coerce').dropna()
    col2_data = pd.to_numeric(df[column2], errors='coerce').dropna()

    # Correlation
    correlation, corr_pvalue = stats.pearsonr(col1_data, col2_data)

    # T-test
    t_stat, t_pvalue = stats.ttest_ind(col1_data, col2_data)

    return {
        'correlation': {
            'coefficient': float(correlation),
            'p_value': float(corr_pvalue),
            'interpretation': 'significant' if corr_pvalue < 0.05 else 'not significant'
        },
        't_test': {
            't_statistic': float(t_stat),
            'p_value': float(t_pvalue),
            'interpretation': 'significantly different' if t_pvalue < 0.05 else 'not significantly different'
        },
        'descriptive_stats': {
            column1: {
                'mean': float(col1_data.mean()),
                'std': float(col1_data.std()),
                'min': float(col1_data.min()),
                'max': float(col1_data.max())
            },
            column2: {
                'mean': float(col2_data.mean()),
                'std': float(col2_data.std()),
                'min': float(col2_data.min()),
                'max': float(col2_data.max())
            }
        }
    }


def validate_data(
    file_path: str,
    sheet_name: Optional[str] = None,
    check_duplicates: bool = True,
    check_outliers: bool = True
) -> Dict[str, Any]:
    """
    Data validation - check for nulls, duplicates, data type issues, outliers

    Args:
        file_path: Path to Excel file
        sheet_name: Sheet name (default: first sheet)
        check_duplicates: Whether to check for duplicate rows
        check_outliers: Whether to detect statistical outliers

    Returns:
        Validation results with issues found
    """
    df = load_dataframe(file_path, sheet_name)

    validation_results = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'null_analysis': {
            'columns_with_nulls': df.columns[df.isnull().any()].tolist(),
            'null_counts': df.isnull().sum().to_dict(),
            'rows_with_any_null': int(df.isnull().any(axis=1).sum())
        }
    }

    # Check duplicates
    if check_duplicates:
        duplicates = df.duplicated()
        validation_results['duplicates'] = {
            'duplicate_rows': int(duplicates.sum()),
            'duplicate_indices': duplicates[duplicates].index.tolist()[:100]  # Limit to first 100
        }

    # Check outliers using IQR method
    if check_outliers:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outliers = {}

        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            outlier_count = outlier_mask.sum()

            if outlier_count > 0:
                outliers[col] = {
                    'count': int(outlier_count),
                    'percentage': float(outlier_count / len(df) * 100),
                    'bounds': {'lower': float(lower_bound), 'upper': float(upper_bound)}
                }

        validation_results['outliers'] = outliers

    return validation_results


def trend_analysis(
    file_path: str,
    time_column: str,
    value_column: str,
    sheet_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Time-series trend analysis with linear regression

    Args:
        file_path: Path to Excel file
        time_column: Column containing time/date values
        value_column: Column containing values to analyze
        sheet_name: Sheet name (default: first sheet)

    Returns:
        Trend analysis results including slope, r-squared, and forecast
    """
    df = load_dataframe(file_path, sheet_name)

    # Convert time column to numeric (days since first date)
    time_data = pd.to_datetime(df[time_column], errors='coerce')
    time_numeric = (time_data - time_data.min()).dt.days

    value_data = pd.to_numeric(df[value_column], errors='coerce')

    # Remove NaN values
    mask = ~(time_numeric.isna() | value_data.isna())
    time_clean = time_numeric[mask]
    value_clean = value_data[mask]

    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(time_clean, value_clean)

    # Calculate moving average
    moving_avg = value_clean.rolling(window=min(7, len(value_clean))).mean()

    return {
        'linear_trend': {
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_value ** 2),
            'p_value': float(p_value),
            'standard_error': float(std_err),
            'trend_direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'flat'
        },
        'statistics': {
            'mean': float(value_clean.mean()),
            'std': float(value_clean.std()),
            'min': float(value_clean.min()),
            'max': float(value_clean.max()),
            'range': float(value_clean.max() - value_clean.min())
        },
        'moving_average': {
            'window_size': min(7, len(value_clean)),
            'current_ma': float(moving_avg.iloc[-1]) if len(moving_avg) > 0 else None
        }
    }


def detect_anomalies(
    file_path: str,
    column: str,
    sheet_name: Optional[str] = None,
    method: str = 'zscore',
    threshold: float = 3.0
) -> Dict[str, Any]:
    """
    Detect anomalies/outliers in data using statistical methods

    Args:
        file_path: Path to Excel file
        column: Column to analyze
        sheet_name: Sheet name (default: first sheet)
        method: Detection method ('zscore' or 'iqr')
        threshold: Z-score threshold (default: 3.0)

    Returns:
        Anomaly detection results
    """
    df = load_dataframe(file_path, sheet_name)

    data = pd.to_numeric(df[column], errors='coerce').dropna()

    if method == 'zscore':
        z_scores = np.abs(stats.zscore(data))
        anomaly_mask = z_scores > threshold
        anomaly_indices = data[anomaly_mask].index.tolist()
        anomaly_values = data[anomaly_mask].tolist()

    elif method == 'iqr':
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        anomaly_mask = (data < lower_bound) | (data > upper_bound)
        anomaly_indices = data[anomaly_mask].index.tolist()
        anomaly_values = data[anomaly_mask].tolist()

    else:
        raise ValueError(f"Unknown method: {method}. Use 'zscore' or 'iqr'")

    return {
        'method': method,
        'total_anomalies': len(anomaly_indices),
        'anomaly_percentage': float(len(anomaly_indices) / len(data) * 100),
        'anomaly_indices': anomaly_indices[:100],  # Limit to first 100
        'anomaly_values': [float(v) for v in anomaly_values[:100]],
        'statistics': {
            'mean': float(data.mean()),
            'std': float(data.std()),
            'min': float(data.min()),
            'max': float(data.max())
        }
    }


def compare_sheets(
    file_path: str,
    sheet1: str,
    sheet2: str,
    key_column: Optional[str] = None
) -> Dict[str, Any]:
    """
    Compare data between two sheets

    Args:
        file_path: Path to Excel file
        sheet1: First sheet name
        sheet2: Second sheet name
        key_column: Column to use as key for comparison (optional)

    Returns:
        Comparison results showing differences
    """
    df1 = load_dataframe(file_path, sheet1)
    df2 = load_dataframe(file_path, sheet2)

    comparison = {
        'shape_comparison': {
            sheet1: {'rows': df1.shape[0], 'columns': df1.shape[1]},
            sheet2: {'rows': df2.shape[0], 'columns': df2.shape[1]}
        },
        'column_comparison': {
            'common_columns': list(set(df1.columns) & set(df2.columns)),
            'only_in_sheet1': list(set(df1.columns) - set(df2.columns)),
            'only_in_sheet2': list(set(df2.columns) - set(df1.columns))
        }
    }

    # If key column specified, compare row-by-row
    if key_column and key_column in df1.columns and key_column in df2.columns:
        merged = pd.merge(df1, df2, on=key_column, how='outer', indicator=True, suffixes=('_sheet1', '_sheet2'))

        comparison['row_comparison'] = {
            'rows_in_both': int((merged['_merge'] == 'both').sum()),
            'rows_only_in_sheet1': int((merged['_merge'] == 'left_only').sum()),
            'rows_only_in_sheet2': int((merged['_merge'] == 'right_only').sum())
        }

    return comparison
