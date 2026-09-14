"""
sheet_tool.py — openpyxl-based spreadsheet read/write and executive workbook creation tools.

Preserves existing formatting and formulas on read-modify-write cycles.
Creates polished, corporate-styled spreadsheets with auto-fitted columns,
navy header bands, alternating zebra striping, accounting borders, and proper number formatting.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from sovereignai.tools.base import Tool, ToolResult
from sovereignai.tools.fs_tools import _validate_path


class SheetRead(Tool):
    name = "sheet_read"
    description = "Read a spreadsheet (.xlsx) into structured rows and cells."
    categories = ["spreadsheet", "planning", "general"]
    json_schema = {
        "type": "object",
        "properties": {
            "path":       {"type": "string",  "description": "Path to .xlsx file"},
            "sheet_name": {"type": "string",  "description": "Sheet name (first sheet if omitted)"},
            "max_rows":   {"type": "integer", "description": "Max rows to read (default: 500)"},
        },
        "required": ["path"],
    }

    def run(self, path: str, sheet_name: str | None = None, max_rows: int = 500) -> ToolResult:
        p = _validate_path(path)
        if p is None:
            return ToolResult.fail(f"Path '{path}' outside workspace.")
        if not p.exists():
            return ToolResult.fail(f"File not found: {path}")

        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(p), data_only=False)
            ws = wb[sheet_name] if sheet_name else wb.active

            rows = []
            for i, row in enumerate(ws.iter_rows(values_only=False)):
                if i >= max_rows:
                    break
                row_data = []
                for cell in row:
                    row_data.append({
                        "cell": cell.coordinate,
                        "value": cell.value,
                        "formula": cell.value if str(cell.value or "").startswith("=") else None,
                    })
                rows.append(row_data)

            return ToolResult.ok({
                "sheet": ws.title,
                "rows": rows,
                "max_row": ws.max_row,
                "max_col": ws.max_column,
                "sheets": wb.sheetnames,
            })
        except ImportError:
            return ToolResult.fail("openpyxl not installed. Run: pip install openpyxl")
        except Exception as e:
            return ToolResult.fail(str(e))


class SheetWrite(Tool):
    name = "sheet_write"
    description = "Update specific cells in an existing .xlsx spreadsheet."
    categories = ["spreadsheet", "planning"]
    json_schema = {
        "type": "object",
        "properties": {
            "path":       {"type": "string", "description": "Path to .xlsx file"},
            "sheet_name": {"type": "string", "description": "Sheet name (first sheet if omitted)"},
            "updates": {
                "type": "array",
                "description": "List of {cell, value} or {cell, formula} updates",
                "items": {
                    "type": "object",
                    "properties": {
                        "cell":    {"type": "string", "description": "Cell ref e.g. 'A1'"},
                        "value":   {"description": "New value"},
                        "formula": {"type": "string", "description": "Formula string e.g. '=SUM(A1:A10)'"},
                    },
                    "required": ["cell"],
                },
            },
        },
        "required": ["path", "updates"],
    }

    def run(self, path: str, updates: list[dict], sheet_name: str | None = None) -> ToolResult:
        p = _validate_path(path)
        if p is None:
            return ToolResult.fail(f"Path '{path}' outside workspace.")
        if not p.exists():
            return ToolResult.fail(f"File not found: {path}")

        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(p))
            ws = wb[sheet_name] if sheet_name else wb.active

            applied = []
            for u in updates:
                cell_ref = u.get("cell")
                formula = u.get("formula")
                value = u.get("value")
                if formula:
                    ws[cell_ref] = formula
                else:
                    ws[cell_ref] = value
                applied.append(cell_ref)

            wb.save(str(p))
            return ToolResult.ok({"updated_cells": applied, "path": str(p)}, file_path=str(p))
        except ImportError:
            return ToolResult.fail("openpyxl not installed.")
        except Exception as e:
            return ToolResult.fail(str(e))


class SheetCreate(Tool):
    name = "sheet_create"
    description = (
        "Create an executive-grade .xlsx spreadsheet workbook with styled navy headers, "
        "auto-fitted columns, alternating row striping, number formatting, and optional totals row."
    )
    categories = ["spreadsheet", "planning", "general"]
    json_schema = {
        "type": "object",
        "properties": {
            "path":       {"type": "string",  "description": "Output file path (.xlsx)"},
            "sheet_name": {"type": "string",  "description": "Sheet name (default: Sheet1)"},
            "headers":    {"type": "array",   "items": {"type": "string"}, "description": "Column headers"},
            "rows": {
                "type": "array",
                "description": "List of row arrays (each row is a list of values)",
                "items": {"type": "array"},
            },
            "summary_row": {
                "type": "array",
                "description": "Optional totals / summary row e.g. ['Total', 45200, 1200, '=AVERAGE(...)']",
            },
            "sheets": {
                "type": "array",
                "description": "Optional multiple sheets: list of {sheet_name, headers, rows, summary_row}",
                "items": {
                    "type": "object",
                    "properties": {
                        "sheet_name": {"type": "string"},
                        "headers": {"type": "array", "items": {"type": "string"}},
                        "rows": {"type": "array", "items": {"type": "array"}},
                        "summary_row": {"type": "array"},
                    },
                    "required": ["sheet_name", "headers", "rows"],
                },
            },
        },
        "required": ["path", "headers"],
    }

    def _parse_val(self, val: Any) -> tuple[Any, str | None, str]:
        """
        Coerce string representations of numbers to int/float with appropriate Excel number formats.
        Returns: (parsed_val, number_format, alignment: 'left'|'center'|'right')
        """
        if val is None:
            return "", None, "center"

        # Direct number types
        if isinstance(val, bool):
            return val, None, "center"
        if isinstance(val, int):
            # If looks like a year (1900..2100), keep as integer without commas
            if 1900 <= val <= 2100:
                return val, "0", "center"
            return val, "#,##0", "right"
        if isinstance(val, float):
            return val, "#,##0.00", "right"

        val_str = str(val).strip()

        # Check if formula
        if val_str.startswith("="):
            return val_str, None, "right"

        # Check for year strings e.g. "2019", "FY 2022"
        if re.match(r"^(19|20)\d\d$", val_str):
            try:
                return int(val_str), "0", "center"
            except ValueError:
                return val_str, None, "center"
        if re.match(r"^FY\s*(19|20)\d\d(-\d\d)?$", val_str, re.IGNORECASE):
            return val_str, None, "center"

        # Check for percentage e.g. "15.4%" or "+8.2%"
        pct_match = re.match(r"^([+-]?\d+(?:\.\d+)?)\s*%$", val_str)
        if pct_match:
            try:
                return float(pct_match.group(1)) / 100.0, "0.0%", "right"
            except ValueError:
                pass

        # Check for currency e.g. "$1,234.56" or "₹45,200" or "$450M"
        curr_match = re.match(r"^[$₹€£]\s*([+-]?[\d,]+(?:\.\d+)?)$", val_str)
        if curr_match:
            clean_num = curr_match.group(1).replace(",", "")
            try:
                f_val = float(clean_num)
                prefix = val_str[0]
                fmt = f'"{prefix}"#,##0.00' if "." in clean_num else f'"{prefix}"#,##0'
                return f_val, fmt, "right"
            except ValueError:
                pass

        # Check for standard comma-separated or plain numbers e.g. "1,234,567.89" or "45000"
        num_match = re.match(r"^([+-]?[\d,]+(?:\.\d+)?)$", val_str)
        if num_match and any(c.isdigit() for c in val_str):
            clean_num = val_str.replace(",", "")
            try:
                if "." in clean_num:
                    return float(clean_num), "#,##0.00", "right"
                else:
                    return int(clean_num), "#,##0", "right"
            except ValueError:
                pass

        return val_str, None, "left"

    def _style_worksheet(
        self,
        ws,
        headers: list[str],
        rows: list[list] | None = None,
        summary_row: list | None = None,
    ) -> None:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        # Color Palette
        NAVY_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        ZEBRA_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

        HDR_FONT = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        REGULAR_FONT = Font(name="Segoe UI", size=10, color="1E293B")
        BOLD_FONT = Font(name="Segoe UI", size=10.5, bold=True, color="0F172A")

        THIN_BORDER = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        SUMMARY_BORDER = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='1E293B'),
            bottom=Side(style='double', color='1E293B')
        )

        # 1. Write Header Row
        ws.row_dimensions[1].height = 28
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=str(h))
            cell.fill = NAVY_FILL
            cell.font = HDR_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = THIN_BORDER

        # 2. Write Data Rows
        current_row = 2
        for row_data in (rows or []):
            ws.row_dimensions[current_row].height = 22
            row_fill = ZEBRA_FILL if current_row % 2 == 0 else WHITE_FILL

            for col_idx in range(1, len(headers) + 1):
                raw_val = row_data[col_idx - 1] if (col_idx - 1) < len(row_data) else ""
                val, num_fmt, align = self._parse_val(raw_val)

                cell = ws.cell(row=current_row, column=col_idx, value=val)
                cell.font = REGULAR_FONT
                cell.fill = row_fill
                cell.border = THIN_BORDER
                cell.alignment = Alignment(horizontal=align, vertical="center")
                if num_fmt:
                    cell.number_format = num_fmt

            current_row += 1

        # 3. Write Summary Row if provided
        if summary_row:
            ws.row_dimensions[current_row].height = 24
            for col_idx in range(1, len(headers) + 1):
                raw_val = summary_row[col_idx - 1] if (col_idx - 1) < len(summary_row) else ""
                val, num_fmt, align = self._parse_val(raw_val)

                cell = ws.cell(row=current_row, column=col_idx, value=val)
                cell.font = BOLD_FONT
                cell.fill = WHITE_FILL
                cell.border = SUMMARY_BORDER
                cell.alignment = Alignment(horizontal=align, vertical="center")
                if num_fmt:
                    cell.number_format = num_fmt
            current_row += 1

        # 4. Auto-fit column widths with breathing room
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            max_len = 0
            for cell in col:
                val_str = str(cell.value or "")
                if val_str.startswith("="):
                    max_len = max(max_len, 10)
                else:
                    max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(14, min(max_len + 4, 50))

        # 5. Freeze Header Pane & Enable Gridlines
        ws.freeze_panes = "A2"
        if ws.views.sheetView:
            ws.views.sheetView[0].showGridLines = True
        ws.auto_filter.ref = ws.dimensions

    def run(
        self,
        path: str,
        headers: list[str],
        rows: list[list] | None = None,
        sheet_name: str = "Sheet1",
        summary_row: list | None = None,
        sheets: list[dict] | None = None,
    ) -> ToolResult:
        p = _validate_path(path)
        if p is None:
            return ToolResult.fail(f"Path '{path}' outside workspace.")

        try:
            import openpyxl
            wb = openpyxl.Workbook()

            if sheets and len(sheets) > 0:
                for idx, s_def in enumerate(sheets):
                    s_name = s_def.get("sheet_name", f"Sheet{idx + 1}")[:31]
                    s_headers = s_def.get("headers", headers)
                    s_rows = s_def.get("rows", [])
                    s_sum = s_def.get("summary_row")

                    ws = wb.active if idx == 0 else wb.create_sheet(title=s_name)
                    ws.title = s_name
                    self._style_worksheet(ws, headers=s_headers, rows=s_rows, summary_row=s_sum)
                sheet_count = len(sheets)
            else:
                ws = wb.active
                ws.title = sheet_name[:31] or "Sheet1"
                self._style_worksheet(ws, headers=headers, rows=rows, summary_row=summary_row)
                sheet_count = 1

            p.parent.mkdir(parents=True, exist_ok=True)
            wb.save(str(p))

            return ToolResult.ok({
                "path": str(p),
                "sheets": sheet_count,
                "rows": len(rows or []),
                "cols": len(headers),
                "size_bytes": p.stat().st_size,
            }, file_path=str(p))

        except ImportError:
            return ToolResult.fail("openpyxl not installed.")
        except Exception as e:
            return ToolResult.fail(str(e))
