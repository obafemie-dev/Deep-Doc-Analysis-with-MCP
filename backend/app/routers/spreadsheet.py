from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional, Any
from pydantic import BaseModel
import os
from pathlib import Path
import io
import pandas as pd

from ..config import settings
from ..services.spreadsheet_service import SpreadsheetService

router = APIRouter(
    prefix=f"{settings.API_V1_STR}/spreadsheet",
    tags=["spreadsheet"],
    responses={404: {"description": "Not found"}}
)

def get_file_path(filename: str) -> Path:
    """Get absolute path to uploaded file and verify existence"""
    # Sanitize filename to prevent directory traversal
    clean_name = os.path.basename(filename)
    file_path = Path(settings.UPLOAD_DIR) / clean_name
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {filename}"
        )
    return file_path

@router.get("/files/{filename}/sheets")
async def get_sheets(filename: str):
    """Get list of sheets in the Excel file"""
    try:
        file_path = get_file_path(filename)
        service = SpreadsheetService(str(file_path))
        return service.get_sheets_list()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/files/{filename}/sheet/{sheet_name}")
async def get_sheet_data(
    filename: str,
    sheet_name: str,
    start_row: int = Query(1, ge=1),
    end_row: int = Query(100, ge=1),
    start_col: int = Query(1, ge=1),
    end_col: int = Query(26, ge=1)
):
    """
    Get data for a specific sheet with viewport pagination.
    Default viewport is A1:Z100.
    """
    try:
        file_path = get_file_path(filename)
        service = SpreadsheetService(str(file_path))
        return service.get_sheet_data(
            sheet_name,
            start_row=start_row,
            end_row=end_row,
            start_col=start_col,
            end_col=end_col
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/files/{filename}/download")
async def download_file(filename: str):
    """Download the original Excel file"""
    file_path = get_file_path(filename)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.get("/files/{filename}/export/csv/{sheet_name}")
async def export_sheet_csv(filename: str, sheet_name: str):
    """Export a specific sheet as CSV"""
    try:
        file_path = get_file_path(filename)
        
        # Use pandas for efficient CSV export
        # read_excel is heavy but reliable for simple value extraction to CSV
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        
        # Create CSV in memory
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = io.BytesIO(stream.getvalue().encode('utf-8'))
        
        return StreamingResponse(
            response,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={sheet_name}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )

@router.get("/files/{filename}/sheet/{sheet_name}/chart/{chart_id}/image")
async def get_chart_image(
    filename: str,
    sheet_name: str,
    chart_id: str,
    width: int = Query(800, ge=200, le=2000),
    height: int = Query(500, ge=150, le=1500)
):
    """
    Render a chart as a PNG image.
    Returns the chart rendered using matplotlib with Excel-like styling.
    """
    try:
        file_path = get_file_path(filename)
        service = SpreadsheetService(str(file_path))
        
        image_bytes = service.render_chart_image(
            sheet_name=sheet_name,
            chart_id=chart_id,
            width=width,
            height=height
        )
        
        return StreamingResponse(
            io.BytesIO(image_bytes),
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename={chart_id}.png",
                "Cache-Control": "public, max-age=300"  # Cache for 5 minutes
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart rendering failed: {str(e)}"
        )

@router.get("/files/{filename}/sheet/{sheet_name}/chart/{chart_id}/plotly")
async def get_chart_plotly_json(
    filename: str,
    sheet_name: str,
    chart_id: str
):
    """
    Get Plotly JSON configuration for a chart.
    Returns the chart configuration for interactive rendering on frontend.
    """
    try:
        file_path = get_file_path(filename)
        service = SpreadsheetService(str(file_path))
        
        chart_json = service.get_chart_plotly_json(
            sheet_name=sheet_name,
            chart_id=chart_id
        )
        
        return chart_json
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart rendering failed: {str(e)}"
        )

class CellUpdateRequest(BaseModel):
    row: int
    col: int
    value: Any

class ChartPositionUpdateRequest(BaseModel):
    row: int
    col: int

class CreateSheetRequest(BaseModel):
    sheet_name: str

@router.post("/files/{filename}/sheet/{sheet_name}/cell")
async def update_cell(
    filename: str,
    sheet_name: str,
    request: CellUpdateRequest
):
    """
    Update a single cell value.
    """
    try:
        file_path = get_file_path(filename)
        service = SpreadsheetService(str(file_path))
        
        result = service.update_cell(
            sheet_name=sheet_name,
            row=request.row,
            col=request.col,
            value=request.value
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cell update failed: {str(e)}"
        )

@router.patch("/files/{filename}/sheet/{sheet_name}/chart/{chart_id}/position")
async def update_chart_position(
    filename: str,
    sheet_name: str,
    chart_id: str,
    request: ChartPositionUpdateRequest
):
    """
    Update the position of a chart on the worksheet.
    """
    try:
        file_path = get_file_path(filename)
        service = SpreadsheetService(str(file_path))
        
        result = service.update_chart_position(
            sheet_name=sheet_name,
            chart_id=chart_id,
            row=request.row,
            col=request.col
        )
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart position update failed: {str(e)}"
        )

@router.post("/files/{filename}/sheets")
async def create_sheet(
    filename: str,
    request: CreateSheetRequest
):
    """
    Create a new sheet in the Excel file.
    """
    try:
        file_path = get_file_path(filename)
        service = SpreadsheetService(str(file_path))
        
        result = service.create_sheet(request.sheet_name)
        
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sheet: {str(e)}"
        )

