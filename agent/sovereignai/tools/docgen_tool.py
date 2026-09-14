"""
docgen_tool.py — Generate executive-grade Word documents, PowerPoint presentations, and Excel files.

These are the "real deliverable" payoffs of the agentic loop.
Every generated file is written to the workspace with high-impact executive styling,
widescreen 16:9 geometry for presentations, structured tables, and clean typography.
"""
from __future__ import annotations

import datetime
from pathlib import Path
import re
from typing import Any

from sovereignai.tools.base import Tool, ToolResult
from sovereignai.tools.fs_tools import _validate_path


# =============================================================================
# DOCX ENGINE (python-docx)
# =============================================================================

def _set_cell_background(cell, hex_color: str) -> None:
    """Set the background fill color of a docx table cell."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_margins(cell, top: int = 100, bottom: int = 100, left: int = 140, right: int = 140) -> None:
    """Set internal cell margins (padding in dxa)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m_name, m_val in (('top', top), ('bottom', bottom), ('left', left), ('right', right)):
        node = OxmlElement(f'w:{m_name}')
        node.set(qn('w:w'), str(m_val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_table_borders(table, color: str = "CBD5E1", sz: str = "4", val: str = "single") -> None:
    """Apply clean subtle horizontal borders to a table."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    tblPr = table._tbl.tblPr
    tblBorders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(tblBorders)


def _add_formatted_text(
    paragraph,
    text: str,
    font_name: str = "Segoe UI",
    font_size: float = 10.5,
    color_rgb: Any = None,
    bold: bool = False,
    italic: bool = False,
) -> None:
    """Parse inline markdown (**bold**, *italic*, `code`) and append styled runs."""
    from docx.shared import Pt, RGBColor

    default_color = color_rgb or RGBColor(30, 41, 59)  # Slate 800
    tokens = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', text)

    for tok in tokens:
        if not tok:
            continue
        run = paragraph.add_run()
        run.font.name = font_name
        run.font.size = Pt(font_size)
        run.font.color.rgb = default_color
        run.bold = bold
        run.italic = italic

        if tok.startswith('**') and tok.endswith('**') and len(tok) >= 4:
            run.text = tok[2:-2]
            run.bold = True
        elif tok.startswith('*') and tok.endswith('*') and len(tok) >= 2:
            run.text = tok[1:-1]
            run.italic = True
        elif tok.startswith('`') and tok.endswith('`') and len(tok) >= 2:
            run.text = tok[1:-1]
            run.font.name = "Consolas"
            run.font.size = Pt(font_size - 0.5)
            run.font.color.rgb = RGBColor(71, 85, 105)
        else:
            run.text = tok


def _render_docx_table(doc, headers: list[str], rows: list[list[str]]) -> None:
    """Render a styled executive data table in docx."""
    from docx.shared import Pt, RGBColor
    from docx.enum.table import WD_TABLE_ALIGNMENT

    if not headers or not rows:
        return

    col_count = len(headers)
    table = doc.add_table(rows=len(rows) + 1, cols=col_count)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(table, color="CBD5E1", sz="4")

    # Header row
    for col_idx, h_text in enumerate(headers):
        cell = table.cell(0, col_idx)
        _set_cell_background(cell, "1E3A8A")  # Deep Navy
        _set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(str(h_text).strip())
        run.font.name = "Segoe UI"
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)

    # Data rows
    for row_idx, row_vals in enumerate(rows, 1):
        bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx in range(col_count):
            val_text = str(row_vals[col_idx]).strip() if col_idx < len(row_vals) else ""
            cell = table.cell(row_idx, col_idx)
            _set_cell_background(cell, bg_color)
            _set_cell_margins(cell, top=90, bottom=90, left=140, right=140)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            _add_formatted_text(
                p,
                val_text,
                font_name="Segoe UI",
                font_size=9.5,
                color_rgb=RGBColor(30, 41, 59),
            )

    # Spacing after table
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(8)


def _render_docx_callout(doc, text: str) -> None:
    """Render an executive callout note with accent border and tinted fill."""
    from docx.shared import Pt, RGBColor
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    _set_cell_background(cell, "F1F5F9")  # Tinted Slate
    _set_cell_margins(cell, top=140, bottom=140, left=180, right=160)

    # Thick left accent border, no other borders
    tblPr = table._tbl.tblPr
    tblBorders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="1E3A8A"/>'
        f'  <w:top w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(tblBorders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    _add_formatted_text(
        p,
        text,
        font_name="Segoe UI",
        font_size=10,
        color_rgb=RGBColor(15, 23, 42),
        italic=True,
    )

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(6)


def _render_markdown_blocks(doc, content: str) -> None:
    """Parse multi-line markdown content into styled paragraphs, bullet lists, and tables."""
    from docx.shared import Pt, RGBColor

    lines = content.splitlines()
    i = 0
    table_lines: list[str] = []

    while i < len(lines):
        line = lines[i].strip()

        # 1. Accumulate Markdown Table lines
        if line.startswith("|") and line.endswith("|"):
            table_lines.append(line)
            i += 1
            continue
        elif table_lines:
            # Render accumulated table
            if len(table_lines) >= 2:
                hdr_parts = [c.strip() for c in table_lines[0].split("|")[1:-1]]
                row_parts = []
                for t_row in table_lines[1:]:
                    # Skip separator row |---|---|
                    if re.match(r"^\|[\s\-:|]+\|$", t_row):
                        continue
                    row_parts.append([c.strip() for c in t_row.split("|")[1:-1]])
                if row_parts:
                    _render_docx_table(doc, hdr_parts, row_parts)
            table_lines = []

        if not line:
            i += 1
            continue

        # 2. Blockquote / Callout (> Note: ...)
        if line.startswith(">"):
            callout_text = line.lstrip("> ").strip()
            _render_docx_callout(doc, callout_text)
            i += 1
            continue

        # 3. Sub-headings inside body (### or ##)
        if line.startswith("### "):
            sub_h = doc.add_paragraph()
            sub_h.paragraph_format.space_before = Pt(10)
            sub_h.paragraph_format.space_after = Pt(4)
            sub_h.paragraph_format.keep_with_next = True
            _add_formatted_text(
                sub_h,
                line[4:].strip(),
                font_name="Segoe UI",
                font_size=11.5,
                color_rgb=RGBColor(51, 65, 85),
                bold=True,
            )
            i += 1
            continue
        elif line.startswith("## "):
            sub_h = doc.add_paragraph()
            sub_h.paragraph_format.space_before = Pt(14)
            sub_h.paragraph_format.space_after = Pt(4)
            sub_h.paragraph_format.keep_with_next = True
            _add_formatted_text(
                sub_h,
                line[3:].strip(),
                font_name="Segoe UI",
                font_size=13,
                color_rgb=RGBColor(37, 99, 235),
                bold=True,
            )
            i += 1
            continue

        # 4. Bullet Points (- item, * item, • item)
        if re.match(r"^[-*•]\s+", line):
            bp_text = re.sub(r"^[-*•]\s+", "", line)
            p_bp = doc.add_paragraph(style="List Bullet")
            p_bp.paragraph_format.space_before = Pt(1)
            p_bp.paragraph_format.space_after = Pt(3)
            p_bp.paragraph_format.line_spacing = 1.15
            _add_formatted_text(p_bp, bp_text, font_name="Segoe UI", font_size=10.5)
            i += 1
            continue

        # 5. Numbered Lists (1. item)
        if re.match(r"^\d+\.\s+", line):
            num_text = re.sub(r"^\d+\.\s+", "", line)
            p_num = doc.add_paragraph(style="List Number")
            p_num.paragraph_format.space_before = Pt(1)
            p_num.paragraph_format.space_after = Pt(3)
            p_num.paragraph_format.line_spacing = 1.15
            _add_formatted_text(p_num, num_text, font_name="Segoe UI", font_size=10.5)
            i += 1
            continue

        # 6. Standard Narrative Paragraph
        p_norm = doc.add_paragraph()
        p_norm.paragraph_format.space_before = Pt(2)
        p_norm.paragraph_format.space_after = Pt(6)
        p_norm.paragraph_format.line_spacing = 1.15
        _add_formatted_text(p_norm, line, font_name="Segoe UI", font_size=10.5)
        i += 1

    # Catch trailing table
    if table_lines and len(table_lines) >= 2:
        hdr_parts = [c.strip() for c in table_lines[0].split("|")[1:-1]]
        row_parts = []
        for t_row in table_lines[1:]:
            if re.match(r"^\|[\s\-:|]+\|$", t_row):
                continue
            row_parts.append([c.strip() for c in t_row.split("|")[1:-1]])
        if row_parts:
            _render_docx_table(doc, hdr_parts, row_parts)


def _build_docx_document(
    title: str,
    sections: list[dict],
    author: str | None = None,
    date: str | None = None,
    subtitle: str | None = None,
    classification: str | None = None,
) -> Any:
    """Build an executive-grade Word document with corporate styling, metadata ribbons, and clean hierarchy."""
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Configure 1-inch margins
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # Document Header & Footer
    sec0 = doc.sections[0]
    footer = sec0.footer
    f_p = footer.paragraphs[0]
    f_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f_run = f_p.add_run("Bastion Sovereign AI Workbench · Sovereign Internal Record")
    f_run.font.name = "Segoe UI"
    f_run.font.size = Pt(8.5)
    f_run.font.italic = True
    f_run.font.color.rgb = RGBColor(148, 163, 184)

    # Document Title Block
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_p.paragraph_format.space_before = Pt(12)
    title_p.paragraph_format.space_after = Pt(4)
    t_run = title_p.add_run(title)
    t_run.font.name = "Segoe UI"
    t_run.font.size = Pt(24)
    t_run.font.bold = True
    t_run.font.color.rgb = RGBColor(15, 23, 42)  # Obsidian

    # Subtitle
    if subtitle:
        sub_p = doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_p.paragraph_format.space_after = Pt(10)
        s_run = sub_p.add_run(subtitle)
        s_run.font.name = "Segoe UI"
        s_run.font.size = Pt(12)
        s_run.font.italic = True
        s_run.font.color.rgb = RGBColor(71, 85, 105)

    # Metadata Ribbon
    meta_parts = [
        f"Author: {author or 'Bastion Sovereign AI'}",
        f"Date: {date or datetime.date.today().strftime('%B %d, %Y')}",
        f"Classification: {classification or 'OFFICIAL / SOVEREIGN AUDITED'}",
    ]
    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta_p.paragraph_format.space_after = Pt(24)
    m_run = meta_p.add_run("  •  ".join(meta_parts))
    m_run.font.name = "Segoe UI"
    m_run.font.size = Pt(9)
    m_run.font.color.rgb = RGBColor(100, 116, 139)

    # Iterate through sections
    for sec_data in sections:
        level = min(max(int(sec_data.get("level", 1)), 1), 3)
        heading_text = sec_data.get("heading", "").strip()

        if heading_text:
            h_p = doc.add_paragraph()
            h_p.paragraph_format.keep_with_next = True

            if level == 1:
                h_p.paragraph_format.space_before = Pt(18)
                h_p.paragraph_format.space_after = Pt(6)
                h_run = h_p.add_run(heading_text)
                h_run.font.name = "Segoe UI"
                h_run.font.size = Pt(15)
                h_run.font.bold = True
                h_run.font.color.rgb = RGBColor(30, 58, 138)  # Deep Corporate Navy
            elif level == 2:
                h_p.paragraph_format.space_before = Pt(14)
                h_p.paragraph_format.space_after = Pt(4)
                h_run = h_p.add_run(heading_text)
                h_run.font.name = "Segoe UI"
                h_run.font.size = Pt(12.5)
                h_run.font.bold = True
                h_run.font.color.rgb = RGBColor(37, 99, 235)  # Cobalt Blue
            else:
                h_p.paragraph_format.space_before = Pt(10)
                h_p.paragraph_format.space_after = Pt(3)
                h_run = h_p.add_run(heading_text)
                h_run.font.name = "Segoe UI"
                h_run.font.size = Pt(11)
                h_run.font.bold = True
                h_run.font.color.rgb = RGBColor(51, 65, 85)  # Slate 700

        # Structured Callout Note
        if sec_data.get("callout"):
            _render_docx_callout(doc, str(sec_data["callout"]))

        # Body narrative
        body_text = sec_data.get("body") or sec_data.get("content") or ""
        if body_text:
            _render_markdown_blocks(doc, body_text)

        # Structured Bullets
        bullets = sec_data.get("bullets") or sec_data.get("bullet_points") or []
        for bp in bullets:
            p_bp = doc.add_paragraph(style="List Bullet")
            p_bp.paragraph_format.space_before = Pt(1)
            p_bp.paragraph_format.space_after = Pt(3)
            p_bp.paragraph_format.line_spacing = 1.15
            _add_formatted_text(p_bp, str(bp), font_name="Segoe UI", font_size=10.5)

        # Structured Table
        tbl_data = sec_data.get("table")
        if isinstance(tbl_data, dict) and tbl_data.get("headers") and tbl_data.get("rows"):
            _render_docx_table(doc, tbl_data["headers"], tbl_data["rows"])

    return doc


class GenDocx(Tool):
    name = "generate_docx"
    description = (
        "Generate an executive-grade Word document (.docx) with formal styling, "
        "structured headings, tables, bullet points, callouts, and corporate metadata ribbon."
    )
    categories = ["general", "planning", "document_qa", "vision"]
    json_schema = {
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Output .docx file path (e.g. 'bylaws_report.docx')",
            },
            "title": {
                "type": "string",
                "description": "Executive document title",
            },
            "subtitle": {
                "type": "string",
                "description": "Document subtitle or descriptive scope note",
            },
            "author": {
                "type": "string",
                "description": "Author or department name",
            },
            "date": {
                "type": "string",
                "description": "Document date",
            },
            "classification": {
                "type": "string",
                "description": "Classification (e.g. 'CONFIDENTIAL / INTERNAL AUDIT')",
            },
            "sections": {
                "type": "array",
                "description": "List of structured sections",
                "items": {
                    "type": "object",
                    "properties": {
                        "heading": {"type": "string", "description": "Section heading"},
                        "level": {"type": "integer", "description": "Heading level 1, 2, or 3"},
                        "body": {"type": "string", "description": "Section narrative (supports markdown formatting, bullets, tables)"},
                        "bullet_points": {"type": "array", "items": {"type": "string"}, "description": "List of key bullets"},
                        "table": {
                            "type": "object",
                            "properties": {
                                "headers": {"type": "array", "items": {"type": "string"}},
                                "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                            },
                        },
                        "callout": {"type": "string", "description": "Highlighted callout / statutory note"},
                    },
                    "required": ["heading"],
                },
            },
        },
        "required": ["output_path", "title", "sections"],
    }

    def run(
        self,
        output_path: str,
        title: str,
        sections: list[dict],
        author: str | None = None,
        date: str | None = None,
        subtitle: str | None = None,
        classification: str | None = None,
    ) -> ToolResult:
        p = _validate_path(output_path)
        if p is None:
            return ToolResult.fail(f"Path '{output_path}' outside workspace.")

        try:
            doc = _build_docx_document(
                title=title,
                sections=sections,
                author=author,
                date=date,
                subtitle=subtitle,
                classification=classification,
            )

            p.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(p))

            size = p.stat().st_size

            return ToolResult.ok(
                {
                    "path": str(p),
                    "size_bytes": size,
                    "sections": len(sections),
                },
                file_path=str(p),
            )

        except ImportError:
            return ToolResult.fail(
                "python-docx not installed. Run: pip install python-docx"
            )
        except Exception as e:
            return ToolResult.fail(str(e))


# =============================================================================
# PPTX ENGINE (python-pptx — 16:9 Modern Widescreen)
# =============================================================================

class GenPptx(Tool):
    name = "generate_pptx"
    description = (
        "Generate a modern 16:9 widescreen PowerPoint presentation (.pptx) with executive "
        "obsidian/navy styling, multi-column cards, KPI stat callouts, tables, and speaker notes."
    )
    categories = ["general", "planning", "vision", "coding"]
    json_schema = {
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Output .pptx file path",
            },
            "title": {
                "type": "string",
                "description": "Presentation deck title",
            },
            "subtitle": {
                "type": "string",
                "description": "Presentation subtitle or theme",
            },
            "presenter": {
                "type": "string",
                "description": "Presenter name or team",
            },
            "slides": {
                "type": "array",
                "description": "List of slides",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Slide title"},
                        "subtitle": {"type": "string", "description": "Category eyebrow or subtitle"},
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of bullet points with bold lead-ins",
                        },
                        "cards": {
                            "type": "array",
                            "description": "2 to 4 multi-column container cards",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "body": {"type": "string"},
                                },
                                "required": ["title", "body"],
                            },
                        },
                        "metrics": {
                            "type": "array",
                            "description": "High-impact KPI callout boxes",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string", "description": "Metric value e.g. '$45.2B'"},
                                    "label": {"type": "string", "description": "Metric label e.g. 'Gross Turnover'"},
                                },
                                "required": ["value", "label"],
                            },
                        },
                        "table": {
                            "type": "object",
                            "properties": {
                                "headers": {"type": "array", "items": {"type": "string"}},
                                "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                            },
                        },
                        "notes": {
                            "type": "string",
                            "description": "Presenter speaker notes",
                        },
                    },
                    "required": ["title"],
                },
            },
        },
        "required": ["output_path", "title", "slides"],
    }

    def run(
        self,
        output_path: str,
        title: str,
        slides: list[dict],
        subtitle: str | None = None,
        presenter: str | None = None,
    ) -> ToolResult:
        p = _validate_path(output_path)
        if p is None:
            return ToolResult.fail(f"Path '{output_path}' outside workspace.")

        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            from pptx.dml.color import RGBColor
            from pptx.enum.shapes import MSO_SHAPE

            prs = Presentation()
            # Modern 16:9 Widescreen Standard
            prs.slide_width = Inches(13.333)
            prs.slide_height = Inches(7.5)

            # Design Palette
            BG_COLOR = RGBColor(11, 15, 25)         # 0B0F19 Obsidian Canvas
            CARD_BG = RGBColor(21, 28, 44)          # 151C2C Lifted Card
            BORDER_COLOR = RGBColor(36, 48, 72)     # 243048 Border line
            ACCENT_COLOR = RGBColor(249, 115, 22)   # F97316 Bastion Signal Orange
            TEXT_WHITE = RGBColor(248, 250, 252)    # F8FAFC
            TEXT_MUTED = RGBColor(148, 163, 184)    # 94A3B8
            TEXT_DIM = RGBColor(100, 116, 139)      # 64748B

            blank_layout = prs.slide_layouts[6]

            # -------------------------------------------------------------
            # SLIDE 1: COVER SLIDE
            # -------------------------------------------------------------
            cover_slide = prs.slides.add_slide(blank_layout)
            c_bg = cover_slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
            c_bg.fill.solid()
            c_bg.fill.fore_color.rgb = BG_COLOR
            c_bg.line.color.rgb = BG_COLOR

            # Top accent stripe
            top_bar = cover_slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.0), Inches(1.2), Inches(0.8), Inches(0.08))
            top_bar.fill.solid()
            top_bar.fill.fore_color.rgb = ACCENT_COLOR
            top_bar.line.color.rgb = ACCENT_COLOR

            # Eyebrow tag
            cat_box = cover_slide.shapes.add_textbox(Inches(1.0), Inches(1.4), Inches(11.3), Inches(0.4))
            tf_cat = cat_box.text_frame
            tf_cat.word_wrap = True
            p_cat = tf_cat.paragraphs[0]
            p_cat.text = "BASTION SOVEREIGN AI  •  EXECUTIVE STRATEGIC BRIEFING"
            p_cat.font.name = "Segoe UI"
            p_cat.font.size = Pt(11)
            p_cat.font.bold = True
            p_cat.font.color.rgb = ACCENT_COLOR

            # Main Deck Title
            title_box = cover_slide.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.3), Inches(2.0))
            tf_title = title_box.text_frame
            tf_title.word_wrap = True
            p_title = tf_title.paragraphs[0]
            p_title.text = title
            p_title.font.name = "Segoe UI"
            p_title.font.size = Pt(38)
            p_title.font.bold = True
            p_title.font.color.rgb = TEXT_WHITE

            # Subtitle
            sub_text = subtitle or "Structured Analysis, Governance Framework, and Strategic Roadmap"
            sub_box = cover_slide.shapes.add_textbox(Inches(1.0), Inches(4.3), Inches(11.3), Inches(1.2))
            tf_sub = sub_box.text_frame
            tf_sub.word_wrap = True
            p_sub = tf_sub.paragraphs[0]
            p_sub.text = sub_text
            p_sub.font.name = "Segoe UI"
            p_sub.font.size = Pt(17)
            p_sub.font.color.rgb = TEXT_MUTED

            # Metadata Footer
            meta_box = cover_slide.shapes.add_textbox(Inches(1.0), Inches(6.4), Inches(11.3), Inches(0.5))
            tf_meta = meta_box.text_frame
            p_meta = tf_meta.paragraphs[0]
            p_meta.text = (
                f"Prepared for: {presenter or 'Executive Leadership'}   |   "
                f"Date: {datetime.date.today().strftime('%B %Y')}   |   "
                f"Security: STRICT SOVEREIGN INTERNAL"
            )
            p_meta.font.name = "Segoe UI"
            p_meta.font.size = Pt(10)
            p_meta.font.color.rgb = TEXT_DIM

            # -------------------------------------------------------------
            # CONTENT SLIDES
            # -------------------------------------------------------------
            total_slides = len(slides) + 1

            for idx, s in enumerate(slides, start=2):
                sl = prs.slides.add_slide(blank_layout)

                # Slide background
                sl_bg = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
                sl_bg.fill.solid()
                sl_bg.fill.fore_color.rgb = BG_COLOR
                sl_bg.line.color.rgb = BG_COLOR

                # Slide Header accent bar
                h_bar = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.6), Inches(0.5), Inches(0.06))
                h_bar.fill.solid()
                h_bar.fill.fore_color.rgb = ACCENT_COLOR
                h_bar.line.color.rgb = ACCENT_COLOR

                # Slide Title & Category
                h_box = sl.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.8))
                tf_h = h_box.text_frame
                tf_h.word_wrap = True
                p_h = tf_h.paragraphs[0]
                p_h.text = s.get("title", "")
                p_h.font.name = "Segoe UI"
                p_h.font.size = Pt(24)
                p_h.font.bold = True
                p_h.font.color.rgb = TEXT_WHITE

                if s.get("subtitle"):
                    p_subh = tf_h.add_paragraph()
                    p_subh.text = s["subtitle"]
                    p_subh.font.name = "Segoe UI"
                    p_subh.font.size = Pt(12)
                    p_subh.font.color.rgb = ACCENT_COLOR

                # Content Rendering Strategy:
                # 1. Metrics (KPI Boxes)
                if s.get("metrics") and len(s["metrics"]) > 0:
                    metrics = s["metrics"][:4]
                    count = len(metrics)
                    gap = Inches(0.35)
                    total_w = Inches(11.7)
                    box_w = (total_w - gap * (count - 1)) / count
                    box_h = Inches(4.5)
                    start_x = Inches(0.8)
                    start_y = Inches(1.8)

                    for m_idx, m_item in enumerate(metrics):
                        mx = start_x + m_idx * (box_w + gap)
                        box_shape = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, mx, start_y, box_w, box_h)
                        box_shape.fill.solid()
                        box_shape.fill.fore_color.rgb = CARD_BG
                        box_shape.line.color.rgb = BORDER_COLOR
                        box_shape.line.width = Pt(1)

                        tbox = sl.shapes.add_textbox(mx + Inches(0.2), start_y + Inches(1.0), box_w - Inches(0.4), box_h - Inches(1.5))
                        tf = tbox.text_frame
                        tf.word_wrap = True
                        p1 = tf.paragraphs[0]
                        p1.text = str(m_item.get("value", ""))
                        p1.font.name = "Segoe UI"
                        p1.font.size = Pt(36)
                        p1.font.bold = True
                        p1.font.color.rgb = ACCENT_COLOR
                        p1.space_after = Pt(12)

                        p2 = tf.add_paragraph()
                        p2.text = str(m_item.get("label", ""))
                        p2.font.name = "Segoe UI"
                        p2.font.size = Pt(14)
                        p2.font.color.rgb = TEXT_WHITE

                # 2. Multi-column Cards (2, 3, or 4 cards)
                elif s.get("cards") and len(s["cards"]) > 0:
                    cards = s["cards"][:4]
                    count = len(cards)
                    gap = Inches(0.35)
                    total_w = Inches(11.7)
                    card_w = (total_w - gap * (count - 1)) / count
                    card_h = Inches(4.5)
                    start_x = Inches(0.8)
                    start_y = Inches(1.8)

                    for c_idx, c_item in enumerate(cards):
                        cx = start_x + c_idx * (card_w + gap)
                        c_shape = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, start_y, card_w, card_h)
                        c_shape.fill.solid()
                        c_shape.fill.fore_color.rgb = CARD_BG
                        c_shape.line.color.rgb = BORDER_COLOR
                        c_shape.line.width = Pt(1)

                        ct_box = sl.shapes.add_textbox(cx + Inches(0.25), start_y + Inches(0.3), card_w - Inches(0.5), card_h - Inches(0.6))
                        ct_tf = ct_box.text_frame
                        ct_tf.word_wrap = True
                        p1 = ct_tf.paragraphs[0]
                        p1.text = str(c_item.get("title", ""))
                        p1.font.name = "Segoe UI"
                        p1.font.size = Pt(16)
                        p1.font.bold = True
                        p1.font.color.rgb = ACCENT_COLOR
                        p1.space_after = Pt(12)

                        p2 = ct_tf.add_paragraph()
                        p2.text = str(c_item.get("body", ""))
                        p2.font.name = "Segoe UI"
                        p2.font.size = Pt(13)
                        p2.font.color.rgb = TEXT_MUTED
                        p2.line_spacing = 1.2

                # 3. Table slide
                elif s.get("table") and s["table"].get("headers") and s["table"].get("rows"):
                    tbl_headers = s["table"]["headers"]
                    tbl_rows = s["table"]["rows"]
                    num_rows = min(len(tbl_rows) + 1, 8)
                    num_cols = len(tbl_headers)

                    table_shape = sl.shapes.add_table(num_rows, num_cols, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.5))
                    table = table_shape.table

                    for c_idx, h_text in enumerate(tbl_headers):
                        cell = table.cell(0, c_idx)
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = RGBColor(30, 41, 59)
                        p = cell.text_frame.paragraphs[0]
                        p.text = str(h_text)
                        p.font.name = "Segoe UI"
                        p.font.size = Pt(13)
                        p.font.bold = True
                        p.font.color.rgb = TEXT_WHITE

                    for r_idx in range(1, num_rows):
                        row_vals = tbl_rows[r_idx - 1]
                        row_fill = CARD_BG if r_idx % 2 == 1 else RGBColor(16, 22, 34)
                        for c_idx in range(num_cols):
                            cell = table.cell(r_idx, c_idx)
                            cell.fill.solid()
                            cell.fill.fore_color.rgb = row_fill
                            val = str(row_vals[c_idx]) if c_idx < len(row_vals) else ""
                            p = cell.text_frame.paragraphs[0]
                            p.text = val
                            p.font.name = "Segoe UI"
                            p.font.size = Pt(12)
                            p.font.color.rgb = TEXT_MUTED

                # 4. Standard Bullets with Container Card
                else:
                    card_container = sl.shapes.add_shape(
                        MSO_SHAPE.ROUNDED_RECTANGLE,
                        Inches(0.8),
                        Inches(1.8),
                        Inches(11.7),
                        Inches(4.5),
                    )
                    card_container.fill.solid()
                    card_container.fill.fore_color.rgb = CARD_BG
                    card_container.line.color.rgb = BORDER_COLOR
                    card_container.line.width = Pt(1)

                    bullets = s.get("bullets") or []
                    b_box = sl.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(10.9), Inches(3.9))
                    b_tf = b_box.text_frame
                    b_tf.word_wrap = True

                    for b_idx, bullet in enumerate(bullets):
                        para = b_tf.paragraphs[0] if b_idx == 0 else b_tf.add_paragraph()
                        para.space_after = Pt(16)
                        para.line_spacing = 1.2

                        # Check for bold lead-in "**Header**: Details..."
                        match = re.match(r"^\*\*(.*?)\*\*[:\-]?\s*(.*)", bullet)
                        if match:
                            r_head = para.add_run()
                            r_head.text = f"•  {match.group(1)}: "
                            r_head.font.name = "Segoe UI"
                            r_head.font.size = Pt(15)
                            r_head.font.bold = True
                            r_head.font.color.rgb = ACCENT_COLOR

                            r_body = para.add_run()
                            r_body.text = match.group(2)
                            r_body.font.name = "Segoe UI"
                            r_body.font.size = Pt(15)
                            r_body.font.color.rgb = TEXT_WHITE
                        else:
                            r = para.add_run()
                            r.text = f"•  {bullet}"
                            r.font.name = "Segoe UI"
                            r.font.size = Pt(15)
                            r.font.color.rgb = TEXT_WHITE

                # Slide Footer
                f_box = sl.shapes.add_textbox(Inches(0.8), Inches(6.8), Inches(11.7), Inches(0.4))
                f_tf = f_box.text_frame
                f_p = f_tf.paragraphs[0]
                f_p.text = f"Slide {idx} of {total_slides}   ·   Bastion Sovereign AI Workbench   ·   Confidential"
                f_p.font.name = "Segoe UI"
                f_p.font.size = Pt(9)
                f_p.font.color.rgb = TEXT_DIM

                # Speaker Notes
                if s.get("notes"):
                    sl.notes_slide.notes_text_frame.text = s["notes"]

            p.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(p))

            return ToolResult.ok(
                {
                    "path": str(p),
                    "size_bytes": p.stat().st_size,
                    "slides": total_slides,
                },
                file_path=str(p),
            )

        except ImportError:
            return ToolResult.fail("python-pptx not installed. Run: pip install python-pptx")
        except Exception as e:
            return ToolResult.fail(str(e))


# =============================================================================
# PDF ENGINE (LibreOffice conversion)
# =============================================================================

class GenPdf(Tool):
    name = "generate_pdf"
    description = (
        "Generate an executive PDF report. Internally creates a Word document "
        "with executive styling then converts it to PDF."
    )
    categories = ["general", "planning", "document_qa", "coding"]
    json_schema = GenDocx.json_schema

    def run(
        self,
        output_path: str,
        title: str,
        sections: list[dict],
        author: str | None = None,
        date: str | None = None,
        subtitle: str | None = None,
        classification: str | None = None,
    ) -> ToolResult:
        import shutil
        import subprocess
        import tempfile

        p = _validate_path(output_path)
        if p is None:
            return ToolResult.fail(f"Path '{output_path}' outside workspace.")

        try:
            doc = _build_docx_document(
                title=title,
                sections=sections,
                author=author,
                date=date,
                subtitle=subtitle,
                classification=classification,
            )

            with tempfile.TemporaryDirectory(prefix="sovai_pdf_") as tmpdir:
                tmp_docx = Path(tmpdir) / "source.docx"
                doc.save(str(tmp_docx))

                subprocess.run(
                    [
                        "soffice",
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        tmpdir,
                        str(tmp_docx),
                    ],
                    check=True,
                    timeout=60,
                    capture_output=True,
                )

                converted = tmp_docx.with_suffix(".pdf")
                if not converted.exists():
                    return ToolResult.fail("LibreOffice completed but no PDF was produced.")

                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(converted, p)

            return ToolResult.ok({"path": str(p)}, file_path=str(p))

        except FileNotFoundError:
            return ToolResult.fail("LibreOffice (soffice) not found — install it for PDF export.")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode(errors="replace") if e.stderr else str(e)
            return ToolResult.fail(f"LibreOffice conversion failed: {stderr}")
        except ImportError:
            return ToolResult.fail("python-docx not installed. Run: pip install python-docx")
        except Exception as e:
            return ToolResult.fail(str(e))


# =============================================================================
# XLSX ENGINE WRAPPER (Delegates to SheetCreate)
# =============================================================================

class GenXlsx(Tool):
    name = "generate_xlsx"
    description = (
        "Generate a styled executive Excel workbook (.xlsx) with auto-fitted columns, "
        "corporate navy headers, alternating row striping, cell borders, and number formatting."
    )
    categories = ["general", "planning", "spreadsheet", "coding"]
    json_schema = {
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Output .xlsx file path",
            },
            "sheet_name": {
                "type": "string",
                "description": "Sheet name (default: Data)",
            },
            "headers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Column headers",
            },
            "rows": {
                "type": "array",
                "items": {"type": "array"},
                "description": "Data rows",
            },
            "summary_row": {
                "type": "array",
                "description": "Optional totals / summary row",
            },
        },
        "required": ["output_path", "headers"],
    }

    def run(
        self,
        output_path: str,
        headers: list[str],
        rows: list[list] | None = None,
        sheet_name: str = "Data",
        summary_row: list | None = None,
    ) -> ToolResult:
        from sovereignai.tools.sheet_tool import SheetCreate

        return SheetCreate().run(
            path=output_path,
            headers=headers,
            rows=rows,
            sheet_name=sheet_name,
            summary_row=summary_row,
        )