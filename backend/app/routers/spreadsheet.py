"""
Spreadsheet router for serving Excel data to the frontend viewer
"""
import io
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
import pandas as pd
import logging

from ..config import settings
from ..services.spreadsheet_service import SpreadsheetService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/spreadsheet",
    tags=["spreadsheet"]
)

UPLOAD_DIR = Path(settings.UPLOAD_DIR)


def get_file_path(filename: str) -> Path:
    """
    Get validated file path

    Args:
        filename: Name of the file

    Returns:
        Path object

    Raises:
        HTTPException: If file not found
    """
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return file_path


@router.get("/files/{filename}/sheets")
async def get_sheets(filename: str):
    """
    Get list of sheets in an Excel file

    Args:
        filename: Name of the Excel file

    Returns:
        List of sheet metadata
    """
    file_path = get_file_path(filename)

    try:
        service = SpreadsheetService(str(file_path))
        sheets = service.get_sheets_list()
        service.close()

        return {
            "filename": filename,
            "sheets": sheets,
            "count": len(sheets)
        }

    except Exception as e:
        logger.error(f"Error getting sheets for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.get("/files/{filename}/sheet/{sheet_name}")
async def get_sheet_data(
    filename: str,
    sheet_name: str,
    start_row: int = Query(1, ge=1, description="Starting row (1-indexed)"),
    end_row: int = Query(100, ge=1, description="Ending row (inclusive)"),
    start_col: int = Query(1, ge=1, description="Starting column (1-indexed)"),
    end_col: int = Query(26, ge=1, description="Ending column (inclusive)")
):
    """
    Get sheet data for a viewport

    Args:
        filename: Name of the Excel file
        sheet_name: Name of the sheet
        start_row: Starting row (1-indexed)
        end_row: Ending row (inclusive)
        start_col: Starting column (1-indexed)
        end_col: Ending column (inclusive)

    Returns:
        Sheet data with cells, merged cells, charts, and dimensions
    """
    file_path = get_file_path(filename)

    try:
        service = SpreadsheetService(str(file_path))
        data = service.get_sheet_data(
            sheet_name=sheet_name,
            start_row=start_row,
            end_row=end_row,
            start_col=start_col,
            end_col=end_col
        )
        service.close()

        return {
            "filename": filename,
            "sheet_name": sheet_name,
            **data
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error getting sheet data for {filename}/{sheet_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading sheet: {str(e)}")


@router.get("/files/{filename}/download")
async def download_file(filename: str):
    """
    Download the Excel file

    Args:
        filename: Name of the Excel file

    Returns:
        FileResponse with the Excel file
    """
    file_path = get_file_path(filename)

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/files/{filename}/export/csv/{sheet_name}")
async def export_sheet_as_csv(filename: str, sheet_name: str):
    """
    Export a sheet as CSV

    Args:
        filename: Name of the Excel file
        sheet_name: Name of the sheet to export

    Returns:
        StreamingResponse with CSV content
    """
    file_path = get_file_path(filename)

    try:
        # Read the specific sheet with pandas
        df = pd.read_excel(str(file_path), sheet_name=sheet_name)

        # Convert to CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Create filename for download
        csv_filename = f"{Path(filename).stem}_{sheet_name}.csv"

        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{csv_filename}"'
            }
        )

    except ValueError as e:
        if "Worksheet" in str(e):
            raise HTTPException(status_code=400, detail=f"Sheet not found: {sheet_name}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Error exporting CSV for {filename}/{sheet_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting CSV: {str(e)}")
