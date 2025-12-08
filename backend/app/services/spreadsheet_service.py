from typing import List, Dict, Any, Optional, Union
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.chart import BarChart, LineChart, PieChart, AreaChart
import datetime
import logging
import io
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import plotly.utils
import json


logger = logging.getLogger(__name__)

class SpreadsheetService:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Load workbook with data_only=True to get values, but we might need another instance for formulas if needed
        # For viewer, we mostly want values. openpyxl doesn't evaluate formulas itself well without external libs,
        # so data_only=True relies on cached values from Excel.
        self.wb = openpyxl.load_workbook(self.file_path, data_only=True, read_only=False) # read_only=False needed for charts

    def get_sheets_list(self) -> List[Dict[str, Any]]:
        """Get list of sheets with metadata"""
        sheets = []
        for name in self.wb.sheetnames:
            ws = self.wb[name]
            
            # Estimate row/col counts - max_row/max_column can be unreliable in openpyxl if not reset
            # but usually fine for a viewer summary
            row_count = ws.max_row or 0
            col_count = ws.max_column or 0
            
            # Check for charts - charts are stored in ws._charts (internal) or ws.charts (public API varies by version)
            # In recent openpyxl, it's ws._charts or we can check ws.drawing
            has_charts = bool(ws._charts) if hasattr(ws, '_charts') else False
            
            sheets.append({
                "name": name,
                "row_count": row_count,
                "col_count": col_count,
                "has_charts": has_charts
            })
        return sheets

    def get_sheet_data(
        self, 
        sheet_name: str, 
        start_row: int = 1, 
        end_row: int = 100, 
        start_col: int = 1, 
        end_col: int = 26
    ) -> Dict[str, Any]:
        """
        Get cell data, merged cells, and charts for a specific sheet and viewport
        """
        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} not found")
            
        ws = self.wb[sheet_name]
        
        # 1. Get Cells Data
        cells = []
        
        # Ensure range is within bounds
        max_row = ws.max_row or 1
        max_col = ws.max_column or 1
        
        end_row = min(end_row, max_row)
        end_col = min(end_col, max_col)
        
        # Iterate through the range
        # iter_rows is efficient
        for row in ws.iter_rows(min_row=start_row, max_row=end_row, min_col=start_col, max_col=end_col):
            for cell in row:
                if cell.value is not None:
                    cell_data = self._process_cell(cell)
                    cells.append(cell_data)
        
        # 2. Get Merged Cells (only those intersecting viewport)
        merged_cells = []
        for range_string in ws.merged_cells:
            min_col, min_row, max_col, max_row = openpyxl.utils.range_boundaries(str(range_string))
            
            # Check intersection
            if (max_row >= start_row and min_row <= end_row and 
                max_col >= start_col and min_col <= end_col):
                merged_cells.append({
                    "start_row": min_row,
                    "start_col": min_col,
                    "end_row": max_row,
                    "end_col": max_col
                })

        # 3. Get Charts
        charts = self._extract_charts(ws)
        
        dimensions = {
            "total_rows": max_row,
            "total_cols": max_col,
            "viewport": {
                "start_row": start_row,
                "end_row": end_row,
                "start_col": start_col,
                "end_col": end_col
            }
        }
        
        return {
            "cells": cells,
            "merged_cells": merged_cells,
            "charts": charts,
            "dimensions": dimensions
        }

    def _process_cell(self, cell) -> Dict[str, Any]:
        """Extract value and style from cell"""
        value = cell.value
        
        # Handle Date serialization
        if isinstance(value, (datetime.datetime, datetime.date)):
            value = value.isoformat()
            
        style = {}
        
        # Extract basic styles
        if cell.font:
            if cell.font.b: style['bold'] = True
            if cell.font.i: style['italic'] = True
            if cell.font.color and hasattr(cell.font.color, 'rgb'):
                # Handle ARGB or RGB
                color = cell.font.color.rgb
                if color and len(str(color)) > 0:
                    # Strip alpha if present (ARGB)
                    style['color'] = f"#{str(color)[2:]}" if len(str(color)) == 8 else f"#{str(color)}"

        if cell.fill and isinstance(cell.fill, PatternFill):
             if cell.fill.fgColor and hasattr(cell.fill.fgColor, 'rgb'):
                bg_color = cell.fill.fgColor.rgb
                if bg_color and len(str(bg_color)) > 0:
                     # Strip alpha if present 00RRGGBB -> RRGGBB
                     hex_bg = str(bg_color)
                     if len(hex_bg) == 8 and hex_bg.startswith('00'):
                         # Excel sometimes treats '00' prefix as alpha 0 (transparent) or just prefix
                         # safely we take last 6 chars for RGB
                         style['background'] = f"#{hex_bg[2:]}"
                     elif len(hex_bg) == 8:
                         # ARGB, just take RGB part
                         style['background'] = f"#{hex_bg[2:]}"
                     else:
                         style['background'] = f"#{hex_bg}"

        return {
            "row": cell.row,
            "col": cell.column,
            "value": value,
            "style": style
        }

    def _extract_charts(self, ws) -> List[Dict[str, Any]]:
        """Extract basic chart metadata from worksheet"""
        charts_data = []
        if not hasattr(ws, '_charts'):
            return []
            
        for i, chart in enumerate(ws._charts):
            try:
                # Determine type
                chart_type = "unknown"
                if isinstance(chart, BarChart): chart_type = "bar"
                elif isinstance(chart, LineChart): chart_type = "line"
                elif isinstance(chart, PieChart): chart_type = "pie"
                elif isinstance(chart, AreaChart): chart_type = "area"
                
                # Get anchor position (top-left)
                # openpyxl charts have an 'anchor' attribute which might be OneCellAnchor or TwoCellAnchor
                anchor_row = 1
                anchor_col = 1
                width = 400
                height = 300
                
                # Handling anchor is tricky in openpyxl as it varies
                if hasattr(chart, 'anchor'):
                    # Try to parse anchor - heavily dependent on implementation
                    # Simplified approach: If it has _from, use it
                    if hasattr(chart.anchor, '_from'):
                        anchor_col = chart.anchor._from.col + 1
                        anchor_row = chart.anchor._from.row + 1
                    
                    # Try to get size (pixels) - purely estimating if not available
                    # openpyxl charts often have width/height in EMU (English Metric Units)
                    # 1 inch = 914400 EMUs
                    # 1 pixel = 9525 EMUs (approx 96 DPI)
                    if hasattr(chart, 'width'): width = chart.width * 96 # often in inches?
                    if hasattr(chart, 'height'): height = chart.height * 96
                
                # Try to extract data references
                chart_data = self._parse_chart_data(chart, ws)
                
                charts_data.append({
                    "id": f"chart_{i}",
                    "type": chart_type,
                    "anchor": {"row": anchor_row, "col": anchor_col},
                    "size": {"width": width, "height": height},
                    "title": chart.title.tx.rich.p[0].r[0].t if (chart.title and hasattr(chart.title, 'tx') and chart.title.tx) else (str(chart.title) if chart.title else "Chart"),
                    "data": chart_data
                })
            except Exception as e:
                logger.warning(f"Failed to parse chart {i}: {e}")
                continue
                
        return charts_data

    def _parse_chart_data(self, chart, ws) -> Dict[str, Any]:
        """
        Attempt to extract data from chart series.
        This is complex because charts ref ranges.
        We will try to resolve the References to actual values.
        """
        labels = []
        datasets = []
        
        try:
            # 1. Extract X-Axis Labels (Categories)
            # Typically in series[0].cat (categorical) or extracted from common x-values
            if chart.series:
                first_series = chart.series[0]
                # Try to get categories from various sources
                if hasattr(first_series, 'cat') and first_series.cat:
                    # Try strRef first (string reference)
                    if hasattr(first_series.cat, 'strRef') and first_series.cat.strRef:
                        labels = self._resolve_reference(first_series.cat.strRef, ws)
                    # Try numRef (numeric reference used as categories)
                    elif hasattr(first_series.cat, 'numRef') and first_series.cat.numRef:
                        labels = self._resolve_reference(first_series.cat.numRef, ws)
                    # Try strLit (string literal)
                    elif hasattr(first_series.cat, 'strLit') and first_series.cat.strLit:
                        labels = [pt.v for pt in first_series.cat.strLit.pt if pt.v]
                    # Try numLit (numeric literal)
                    elif hasattr(first_series.cat, 'numLit') and first_series.cat.numLit:
                        labels = [pt.v for pt in first_series.cat.numLit.pt if pt.v]
                
                # If no categories found, try xVal for scatter/line charts
                if not labels and hasattr(first_series, 'xVal') and first_series.xVal:
                    if hasattr(first_series.xVal, 'numRef') and first_series.xVal.numRef:
                        labels = self._resolve_reference(first_series.xVal.numRef, ws)
                    elif hasattr(first_series.xVal, 'numLit') and first_series.xVal.numLit:
                        labels = [pt.v for pt in first_series.xVal.numLit.pt if pt.v]
            
            # 2. Extract Datasets (Series)
            for idx, s in enumerate(chart.series):
                label = f"Series {idx + 1}"
                
                # Get series title
                if hasattr(s, 'tx') and s.tx:
                    if hasattr(s.tx, 'strRef') and s.tx.strRef:
                        title_vals = self._resolve_reference(s.tx.strRef, ws)
                        if title_vals: label = str(title_vals[0])
                    elif hasattr(s.tx, 'v') and s.tx.v:
                        label = str(s.tx.v)
                
                values = []
                
                # Try val (for bar/line/area charts)
                if hasattr(s, 'val') and s.val:
                    if hasattr(s.val, 'numRef') and s.val.numRef:
                        values = self._resolve_reference(s.val.numRef, ws)
                    elif hasattr(s.val, 'numLit') and s.val.numLit:
                        values = [pt.v for pt in s.val.numLit.pt if pt.v is not None]
                
                # Try yVal for scatter charts
                if not values and hasattr(s, 'yVal') and s.yVal:
                    if hasattr(s.yVal, 'numRef') and s.yVal.numRef:
                        values = self._resolve_reference(s.yVal.numRef, ws)
                    elif hasattr(s.yVal, 'numLit') and s.yVal.numLit:
                        values = [pt.v for pt in s.yVal.numLit.pt if pt.v is not None]
                
                # Convert values to float where possible
                cleaned_values = []
                for v in values:
                    if v is not None:
                        try:
                            cleaned_values.append(float(v))
                        except (ValueError, TypeError):
                            cleaned_values.append(v)
                    else:
                        cleaned_values.append(0)
                
                datasets.append({
                    "label": label,
                    "data": cleaned_values
                })
            
            # Generate labels if still empty (use indices)
            if not labels and datasets:
                max_len = max(len(ds['data']) for ds in datasets) if datasets else 0
                labels = [str(i + 1) for i in range(max_len)]
                
        except Exception as e:
            logger.warning(f"Error parsing chart series: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            
        return {
            "labels": labels,
            "datasets": datasets
        }

    def _resolve_reference(self, reference, ws_context) -> List[Any]:
        """
        Resolve an Excel chart reference (e.g., 'Sheet1!$A$2:$A$10') to a list of values.
        """
        try:
            # openpyxl Chart references are objects usually, but sometimes strings if we query .f
            # If it's a Reference object with f (formula)
            f = reference.f if hasattr(reference, 'f') else str(reference)
            
            # Parse sheet and range
            if '!' in f:
                sheet_name, range_str = f.split('!', 1)
                # Strip quotes from sheet name if present
                sheet_name = sheet_name.replace("'", "")
                ws = self.wb[sheet_name] if sheet_name in self.wb.sheetnames else ws_context
            else:
                ws = ws_context
                range_str = f

            values = []
            # Handle whole columns/rows if passed? (charts usually use specific ranges)
            # range_str like $A$1:$A$10
            # openpyxl requires un-anchored range for iter_rows sometimes? No, range boundaries handles $
            min_col, min_row, max_col, max_row = openpyxl.utils.range_boundaries(range_str)
            
            for row in ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
                for cell in row:
                    values.append(cell.value)
            
            return values
        except Exception as e:
            logger.warning(f"Failed to resolve reference {reference}: {e}")
            return []

    def render_chart_image(self, sheet_name: str, chart_id: str, width: int = 800, height: int = 500) -> bytes:
        """
        Render a chart as a PNG image using matplotlib.
        Returns PNG bytes.
        """
        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} not found")
            
        ws = self.wb[sheet_name]
        
        # Find chart by id
        if not hasattr(ws, '_charts') or not ws._charts:
            raise ValueError(f"No charts found in sheet {sheet_name}")
        
        chart_index = int(chart_id.replace("chart_", ""))
        if chart_index >= len(ws._charts):
            raise ValueError(f"Chart {chart_id} not found")
            
        chart = ws._charts[chart_index]
        
        # Get chart data
        chart_data = self._parse_chart_data(chart, ws)
        chart_type = "bar"
        if isinstance(chart, BarChart): chart_type = "bar"
        elif isinstance(chart, LineChart): chart_type = "line"
        elif isinstance(chart, PieChart): chart_type = "pie"
        elif isinstance(chart, AreaChart): chart_type = "area"
        
        # Get title
        title = "Chart"
        try:
            if chart.title and hasattr(chart.title, 'tx') and chart.title.tx:
                title = chart.title.tx.rich.p[0].r[0].t
            elif chart.title:
                title = str(chart.title)
        except:
            pass
        
        # Create figure
        dpi = 100
        fig, ax = plt.subplots(figsize=(width/dpi, height/dpi), dpi=dpi)
        
        # Apply Excel-like styling
        plt.style.use('seaborn-v0_8-whitegrid')
        ax.set_facecolor('#FFFFFF')
        fig.patch.set_facecolor('#FFFFFF')
        
        # Prepare data
        labels = chart_data.get('labels', [])
        datasets = chart_data.get('datasets', [])
        
        # If no labels, try to use first dataset as labels and second as data
        if not labels and len(datasets) >= 2:
            first_ds = datasets[0]['data']
            second_ds = datasets[1]['data']
            
            # Filter to valid entries
            valid_data = []
            for i, (label, val) in enumerate(zip(first_ds, second_ds)):
                if label is None or (isinstance(label, str) and ('Unnamed' in label or label.lower() == 'year')):
                    continue
                if isinstance(val, (int, float)):
                    valid_data.append((str(label), float(val)))
            
            if valid_data:
                labels = [d[0] for d in valid_data]
                datasets = [{'label': 'Value', 'data': [d[1] for d in valid_data]}]
        
        if not labels or not datasets:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center', fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        else:
            # Limit data points to prevent overcrowded charts
            MAX_POINTS = 50
            if len(labels) > MAX_POINTS:
                # Sample evenly across the data
                step = len(labels) // MAX_POINTS
                indices = list(range(0, len(labels), step))[:MAX_POINTS]
                labels = [labels[i] for i in indices]
                for ds in datasets:
                    ds['data'] = [ds['data'][i] for i in indices if i < len(ds['data'])]
            
            # Excel-like colors
            colors = ['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5', '#70AD47']
            
            if chart_type == 'bar':
                x = np.arange(len(labels))
                bar_width = 0.8 / len(datasets)
                
                for i, ds in enumerate(datasets):
                    values = [v if isinstance(v, (int, float)) else 0 for v in ds['data'][:len(labels)]]
                    offset = (i - len(datasets)/2 + 0.5) * bar_width
                    bars = ax.bar(x + offset, values, bar_width, label=ds.get('label', f'Series {i+1}'), 
                                 color=colors[i % len(colors)], edgecolor='white')
                
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
                ax.set_ylabel('Value', fontsize=10)
                
            elif chart_type == 'line':
                x = np.arange(len(labels))
                
                for i, ds in enumerate(datasets):
                    values = [v if isinstance(v, (int, float)) else 0 for v in ds['data'][:len(labels)]]
                    ax.plot(x, values, marker='o', label=ds.get('label', f'Series {i+1}'),
                           color=colors[i % len(colors)], linewidth=2, markersize=5)
                
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
                ax.set_ylabel('Value', fontsize=10)
                
            elif chart_type == 'pie':
                values = [v if isinstance(v, (int, float)) else 0 for v in datasets[0]['data'][:len(labels)]]
                # Filter out zero values
                pie_data = [(l, v) for l, v in zip(labels, values) if v > 0]
                if pie_data:
                    pie_labels, pie_values = zip(*pie_data)
                    wedges, texts, autotexts = ax.pie(pie_values, labels=pie_labels, autopct='%1.1f%%',
                                                       colors=colors[:len(pie_values)], 
                                                       textprops={'fontsize': 9})
                    ax.axis('equal')
                    
            elif chart_type == 'area':
                x = np.arange(len(labels))
                
                for i, ds in enumerate(datasets):
                    values = [v if isinstance(v, (int, float)) else 0 for v in ds['data'][:len(labels)]]
                    ax.fill_between(x, values, alpha=0.6, label=ds.get('label', f'Series {i+1}'),
                                   color=colors[i % len(colors)])
                    ax.plot(x, values, color=colors[i % len(colors)], linewidth=1)
                
                ax.set_xticks(x)
                ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
                ax.set_ylabel('Value', fontsize=10)
            
            # Add legend if multiple datasets
            if len(datasets) > 1 and chart_type != 'pie':
                ax.legend(fontsize=9, frameon=True, facecolor='white', edgecolor='#CCCCCC')
        
        # Set title
        ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
        
        # Style axes
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#CCCCCC')
        ax.spines['bottom'].set_color('#CCCCCC')
        ax.tick_params(colors='#666666')
        ax.yaxis.grid(True, linestyle='--', alpha=0.7, color='#E0E0E0')
        ax.xaxis.grid(False)
        
        plt.tight_layout()
        
        # Save to bytes
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
        buf.seek(0)
        plt.close(fig)
        
        return buf.getvalue()

    def get_chart_plotly_json(self, sheet_name: str, chart_id: str) -> Dict[str, Any]:
        """
        Generate Plotly JSON configuration for a chart.
        """
        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} not found")
            
        ws = self.wb[sheet_name]
        
        # Find chart by id
        if not hasattr(ws, '_charts') or not ws._charts:
            raise ValueError(f"No charts found in sheet {sheet_name}")
        
        chart_index = int(chart_id.replace("chart_", ""))
        if chart_index >= len(ws._charts):
            raise ValueError(f"Chart {chart_id} not found")
            
        chart = ws._charts[chart_index]
        
        # Get chart data
        chart_data = self._parse_chart_data(chart, ws)
        chart_type = "bar"
        if isinstance(chart, BarChart): chart_type = "bar"
        elif isinstance(chart, LineChart): chart_type = "line"
        elif isinstance(chart, PieChart): chart_type = "pie"
        elif isinstance(chart, AreaChart): chart_type = "area"
        
        # Get title
        title = "Chart"
        try:
            if chart.title and hasattr(chart.title, 'tx') and chart.title.tx:
                title = chart.title.tx.rich.p[0].r[0].t
            elif chart.title:
                title = str(chart.title)
        except:
            pass
            
        # Prepare data
        labels = chart_data.get('labels', [])
        datasets = chart_data.get('datasets', [])
        
        # If no labels, try to use first dataset as labels and second as data
        if not labels and len(datasets) >= 2:
            first_ds = datasets[0]['data']
            second_ds = datasets[1]['data']
            
            # Filter to valid entries
            valid_data = []
            for i, (label, val) in enumerate(zip(first_ds, second_ds)):
                if label is None or (isinstance(label, str) and ('Unnamed' in label or label.lower() == 'year')):
                    continue
                if isinstance(val, (int, float)):
                    valid_data.append((str(label), float(val)))
            
            if valid_data:
                labels = [d[0] for d in valid_data]
                datasets = [{'label': 'Value', 'data': [d[1] for d in valid_data]}]

        # Limit data points to prevent performance issues
        MAX_POINTS = 100
        if len(labels) > MAX_POINTS:
            step = len(labels) // MAX_POINTS
            indices = list(range(0, len(labels), step))[:MAX_POINTS]
            labels = [labels[i] for i in indices]
            for ds in datasets:
                ds['data'] = [ds['data'][i] for i in indices if i < len(ds['data'])]

        # Construct Plotly Figure
        data = []
        colors = ['#4472C4', '#ED7D31', '#A5A5A5', '#FFC000', '#5B9BD5', '#70AD47']
        
        for i, ds in enumerate(datasets):
            values = [v if isinstance(v, (int, float)) else 0 for v in ds['data'][:len(labels)]]
            series_name = ds.get('label', f'Series {i+1}')
            color = colors[i % len(colors)]
            
            trace = {}
            if chart_type == 'bar':
                trace = go.Bar(x=labels, y=values, name=series_name, marker_color=color)
            elif chart_type == 'line':
                trace = go.Scatter(x=labels, y=values, mode='lines+markers', name=series_name, line=dict(color=color, width=2))
            elif chart_type == 'pie':
                # For pie, we usually take the first dataset
                if i == 0:
                    pie_data = [(l, v) for l, v in zip(labels, values) if v > 0]
                    if pie_data:
                        pie_labels, pie_values = zip(*pie_data)
                        trace = go.Pie(labels=pie_labels, values=pie_values, marker=dict(colors=colors))
            elif chart_type == 'area':
                trace = go.Scatter(x=labels, y=values, mode='lines', fill='tozeroy', name=series_name, line=dict(color=color))
            
            if trace:
                data.append(trace)

        layout = {
            "title": {"text": title, "font": {"size": 16, "family": "Arial, sans-serif"}},
            "margin": {"l": 50, "r": 20, "t": 60, "b": 50},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
            "showlegend": True,
            "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            "xaxis": {"showgrid": False, "tickangle": -45, "automargin": True},
            "yaxis": {"showgrid": True, "gridcolor": "#E0E0E0", "zeroline": True, "zerolinecolor": "#E0E0E0"}
        }

        fig = go.Figure(data=data, layout=layout)
        
        # Return as JSON-compatible dict using Plotly's utils
        return json.loads(json.dumps(fig.to_dict(), cls=plotly.utils.PlotlyJSONEncoder))

    def update_cell(self, sheet_name: str, row: int, col: int, value: Any) -> Dict[str, Any]:
        """
        Update a cell value in the spreadsheet.
        Row and col are 1-based indices.
        """
        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} not found")
            
        ws = self.wb[sheet_name]
        
        # Update cell
        cell = ws.cell(row=row, column=col)
        
        # Handle types (simple conversion)
        try:
            if isinstance(value, str):
                if value.lower() == 'true': value = True
                elif value.lower() == 'false': value = False
                elif value.replace('.', '', 1).isdigit():
                    if '.' in value: value = float(value)
                    else: value = int(value)
        except:
            pass
            
        cell.value = value
        
        # Save workbook
        self.wb.save(self.file_path)
        
        return {
            "message": "Cell updated successfully",
            "row": row,
            "col": col,
            "value": value
        }

    def update_chart_position(self, sheet_name: str, chart_id: str, row: int, col: int) -> Dict[str, Any]:
        """
        Update the position (anchor) of a chart on the worksheet.
        Row and col are 1-based indices representing the top-left cell position.
        """
        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} not found")
            
        ws = self.wb[sheet_name]
        
        # Find chart by id
        if not hasattr(ws, '_charts') or not ws._charts:
            raise ValueError(f"No charts found in sheet {sheet_name}")
        
        chart_index = int(chart_id.replace("chart_", ""))
        if chart_index >= len(ws._charts):
            raise ValueError(f"Chart {chart_id} not found")
            
        chart = ws._charts[chart_index]
        
        # Update chart anchor position
        # Convert to cell address (e.g., "E5")
        cell_address = f"{get_column_letter(col)}{row}"
        
        # Create a new anchor for the chart
        # openpyxl uses anchor objects; for simplicity, we can reassign
        from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, AnchorMarker
        from openpyxl.utils.units import pixels_to_EMU
        
        # Get current size if available
        width = getattr(chart, 'width', 15)  # width in cm
        height = getattr(chart, 'height', 10)  # height in cm
        
        # Create new anchor marker
        marker = AnchorMarker(col=col-1, row=row-1)  # openpyxl uses 0-based for markers
        
        # Set the anchor
        # Note: openpyxl chart anchors can be tricky. The simplest approach is to
        # remove and re-add the chart, but that's destructive.
        # Instead, we'll modify the anchor if it exists
        if hasattr(chart, 'anchor'):
            if hasattr(chart.anchor, '_from'):
                chart.anchor._from.col = col - 1
                chart.anchor._from.row = row - 1
        
        # Save workbook
        self.wb.save(self.file_path)
        
        return {
            "message": "Chart position updated successfully",
            "chart_id": chart_id,
            "row": row,
            "col": col,
            "cell_address": cell_address
        }

    def create_sheet(self, sheet_name: str) -> Dict[str, Any]:
        """
        Create a new sheet in the workbook.
        """
        if sheet_name in self.wb.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' already exists")
        
        # Create new sheet
        self.wb.create_sheet(sheet_name)
        
        # Save workbook
        self.wb.save(self.file_path)
        
        return {
            "message": f"Sheet '{sheet_name}' created successfully",
            "sheet_name": sheet_name
        }
