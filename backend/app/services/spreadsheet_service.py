"""
Spreadsheet service for reading Excel files and extracting data/charts for the viewer
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import logging

logger = logging.getLogger(__name__)


class SpreadsheetService:
    """Service for reading Excel files and extracting data for the spreadsheet viewer"""

    def __init__(self, file_path: str):
        """
        Initialize the service with a file path

        Args:
            file_path: Path to the Excel file
        """
        self.file_path = file_path
        self._workbook = None

    def _get_workbook(self):
        """Lazy load workbook"""
        if self._workbook is None:
            self._workbook = load_workbook(self.file_path, data_only=True)
        return self._workbook

    def get_sheets_list(self) -> List[Dict[str, Any]]:
        """
        Get list of sheets with metadata

        Returns:
            List of sheet info dicts with name, row_count, col_count, has_charts
        """
        wb = self._get_workbook()
        sheets = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            has_charts = len(ws._charts) > 0 if hasattr(ws, '_charts') else False

            sheets.append({
                "name": sheet_name,
                "row_count": ws.max_row or 0,
                "col_count": ws.max_column or 0,
                "has_charts": has_charts
            })

        return sheets

    def _serialize_value(self, value: Any) -> Any:
        """
        Serialize cell value to JSON-safe format

        Args:
            value: Cell value to serialize

        Returns:
            JSON-serializable value
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)

    def _get_cell_style(self, cell) -> Dict[str, Any]:
        """
        Extract style information from a cell

        Args:
            cell: openpyxl cell object

        Returns:
            Dict with style properties
        """
        style = {}

        try:
            font = cell.font
            if font:
                if font.bold:
                    style["bold"] = True
                if font.italic:
                    style["italic"] = True
                if font.color and font.color.rgb and font.color.rgb != "00000000":
                    # Convert ARGB to RGB hex
                    rgb = font.color.rgb
                    if isinstance(rgb, str) and len(rgb) >= 6:
                        style["color"] = f"#{rgb[-6:]}"

            fill = cell.fill
            if fill and fill.fgColor and fill.fgColor.rgb:
                rgb = fill.fgColor.rgb
                if isinstance(rgb, str) and len(rgb) >= 6 and rgb != "00000000":
                    style["background"] = f"#{rgb[-6:]}"

        except Exception as e:
            logger.debug(f"Error extracting cell style: {e}")

        return style if style else None

    def get_sheet_data(
        self,
        sheet_name: str,
        start_row: int = 1,
        end_row: int = 100,
        start_col: int = 1,
        end_col: int = 26
    ) -> Dict[str, Any]:
        """
        Get sheet data for a viewport

        Args:
            sheet_name: Name of the sheet
            start_row: Starting row (1-indexed)
            end_row: Ending row (inclusive)
            start_col: Starting column (1-indexed)
            end_col: Ending column (inclusive)

        Returns:
            Dict with cells, merged_cells, charts, and dimensions
        """
        wb = self._get_workbook()

        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found")

        ws = wb[sheet_name]

        # Clamp ranges to actual data
        max_row = min(end_row, ws.max_row or 1)
        max_col = min(end_col, ws.max_column or 1)

        # Extract cells
        cells = []
        for row in range(start_row, max_row + 1):
            for col in range(start_col, max_col + 1):
                cell = ws.cell(row=row, column=col)
                cell_data = {
                    "row": row,
                    "col": col,
                    "value": self._serialize_value(cell.value)
                }
                style = self._get_cell_style(cell)
                if style:
                    cell_data["style"] = style
                cells.append(cell_data)

        # Extract merged cells in viewport
        merged_cells = []
        for merged_range in ws.merged_cells.ranges:
            if (merged_range.min_row <= max_row and merged_range.max_row >= start_row and
                merged_range.min_col <= max_col and merged_range.max_col >= start_col):
                merged_cells.append({
                    "start_row": merged_range.min_row,
                    "start_col": merged_range.min_col,
                    "end_row": merged_range.max_row,
                    "end_col": merged_range.max_col
                })

        # Extract charts
        charts = self._extract_charts(ws)

        return {
            "cells": cells,
            "merged_cells": merged_cells,
            "charts": charts,
            "dimensions": {
                "total_rows": ws.max_row or 0,
                "total_cols": ws.max_column or 0,
                "viewport": {
                    "start_row": start_row,
                    "end_row": max_row,
                    "start_col": start_col,
                    "end_col": max_col
                }
            }
        }

    def _extract_charts(self, ws) -> List[Dict[str, Any]]:
        """
        Extract chart data from worksheet

        Args:
            ws: openpyxl worksheet object

        Returns:
            List of chart data dicts
        """
        charts = []

        if not hasattr(ws, '_charts') or not ws._charts:
            return charts

        for idx, chart in enumerate(ws._charts):
            try:
                chart_data = self._parse_chart(chart, ws, idx)
                if chart_data:
                    charts.append(chart_data)
            except Exception as e:
                logger.warning(f"Error parsing chart {idx}: {e}")

        return charts

    def _parse_chart(self, chart, ws, idx: int) -> Optional[Dict[str, Any]]:
        """
        Parse a single chart object

        Args:
            chart: openpyxl chart object
            ws: worksheet containing the chart
            idx: chart index

        Returns:
            Chart data dict or None
        """
        # Determine chart type
        chart_type = self._get_chart_type(chart)

        # Get anchor position
        anchor_row = 1
        anchor_col = 1
        if hasattr(chart, 'anchor') and chart.anchor:
            try:
                if hasattr(chart.anchor, '_from'):
                    anchor_row = chart.anchor._from.row + 1
                    anchor_col = chart.anchor._from.col + 1
            except Exception:
                pass

        # Get chart dimensions (default size if not available)
        width = 400
        height = 300
        if hasattr(chart, 'width') and chart.width:
            width = int(chart.width * 96 / 914400)  # EMUs to pixels
        if hasattr(chart, 'height') and chart.height:
            height = int(chart.height * 96 / 914400)

        # Get title
        title = None
        if hasattr(chart, 'title') and chart.title:
            if hasattr(chart.title, 'tx') and chart.title.tx:
                if hasattr(chart.title.tx, 'rich') and chart.title.tx.rich:
                    try:
                        paragraphs = chart.title.tx.rich.paragraphs
                        if paragraphs:
                            for p in paragraphs:
                                if hasattr(p, 'text'):
                                    title = p.text
                                    break
                                elif hasattr(p, 'r') and p.r:
                                    for r in p.r:
                                        if hasattr(r, 't') and r.t:
                                            title = r.t
                                            break
                    except Exception:
                        pass

        # Extract data from chart series
        labels = []
        datasets = []

        try:
            series_list = list(chart.series) if chart.series else []

            for series_idx, series in enumerate(series_list):
                dataset = {
                    "label": f"Series {series_idx + 1}",
                    "data": [],
                    "type": chart_type
                }

                # Try to get series title
                if hasattr(series, 'title') and series.title:
                    dataset["label"] = str(series.title)

                # Extract values
                if hasattr(series, 'val') and series.val:
                    values = self._extract_series_values(series.val, ws)
                    dataset["data"] = values

                # Extract categories/labels from first series only
                if series_idx == 0 and hasattr(series, 'cat') and series.cat:
                    labels = self._extract_series_labels(series.cat, ws)

                datasets.append(dataset)

        except Exception as e:
            logger.warning(f"Error extracting chart series data: {e}")

        return {
            "id": f"chart_{idx}",
            "type": chart_type,
            "anchor": {"row": anchor_row, "col": anchor_col},
            "size": {"width": width, "height": height},
            "title": title,
            "data": {
                "labels": labels,
                "datasets": datasets
            }
        }

    def _get_chart_type(self, chart) -> str:
        """Determine chart type from openpyxl chart object"""
        class_name = chart.__class__.__name__.lower()

        if 'bar' in class_name:
            return 'bar'
        elif 'line' in class_name:
            return 'line'
        elif 'pie' in class_name or 'doughnut' in class_name:
            return 'pie'
        elif 'area' in class_name:
            return 'area'
        elif 'scatter' in class_name:
            return 'scatter'
        elif 'combo' in class_name:
            return 'combo'
        else:
            return 'bar'  # Default

    def _extract_series_values(self, val_ref, ws) -> List[Any]:
        """Extract numeric values from a series value reference"""
        values = []

        try:
            if hasattr(val_ref, 'numRef') and val_ref.numRef:
                # Reference to cells
                ref = val_ref.numRef.f
                values = self._get_values_from_range(ref, ws)
            elif hasattr(val_ref, 'numLit') and val_ref.numLit:
                # Literal values
                for pt in val_ref.numLit.pt:
                    try:
                        values.append(float(pt.v))
                    except (ValueError, TypeError):
                        values.append(0)
        except Exception as e:
            logger.debug(f"Error extracting series values: {e}")

        return values

    def _extract_series_labels(self, cat_ref, ws) -> List[str]:
        """Extract category labels from a series category reference"""
        labels = []

        try:
            if hasattr(cat_ref, 'strRef') and cat_ref.strRef:
                ref = cat_ref.strRef.f
                values = self._get_values_from_range(ref, ws)
                labels = [str(v) if v is not None else '' for v in values]
            elif hasattr(cat_ref, 'numRef') and cat_ref.numRef:
                ref = cat_ref.numRef.f
                values = self._get_values_from_range(ref, ws)
                labels = [str(v) if v is not None else '' for v in values]
            elif hasattr(cat_ref, 'strLit') and cat_ref.strLit:
                for pt in cat_ref.strLit.pt:
                    labels.append(str(pt.v) if pt.v else '')
        except Exception as e:
            logger.debug(f"Error extracting series labels: {e}")

        return labels

    def _get_values_from_range(self, range_str: str, ws) -> List[Any]:
        """
        Get cell values from a range reference string

        Args:
            range_str: Range string like "Sheet1!$A$1:$A$10"
            ws: Worksheet object

        Returns:
            List of cell values
        """
        values = []

        try:
            # Parse range string
            if '!' in range_str:
                sheet_ref, cell_range = range_str.split('!', 1)
                # Remove quotes from sheet name
                sheet_ref = sheet_ref.strip("'")
                # Get the correct worksheet
                wb = self._get_workbook()
                if sheet_ref in wb.sheetnames:
                    ws = wb[sheet_ref]
            else:
                cell_range = range_str

            # Remove $ signs
            cell_range = cell_range.replace('$', '')

            # Get cells
            for cell in ws[cell_range]:
                if isinstance(cell, tuple):
                    for c in cell:
                        values.append(self._serialize_value(c.value))
                else:
                    values.append(self._serialize_value(cell.value))

        except Exception as e:
            logger.debug(f"Error getting values from range {range_str}: {e}")

        return values

    def close(self):
        """Close the workbook"""
        if self._workbook:
            self._workbook.close()
            self._workbook = None
