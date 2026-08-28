"""
vision_tool.py — Image and scanned PDF understanding via the vision-language model.

Pipeline: image/PDF path → rasterize (if PDF) → vision model → structured JSON
The output feeds directly into the general model in the same agent turn.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import ollama

from sovereignai.config import get_config
from sovereignai.tools.base import Tool, ToolResult
from sovereignai.tools.fs_tools import _validate_path

_VISION_PROMPT = """\
Extract all readable text, labels, and key findings from this image.
Return JSON:
{
  "raw_text": "...",
  "key_findings": ["...", "..."],
  "tables": [{"headers": [...], "rows": [[...]]}],
  "handwritten_notes": ["..."],
  "confidence": "high|medium|low"
}
If handwriting is illegible, say so explicitly rather than guessing.
Return ONLY valid JSON, no explanation."""


def _image_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _rasterize_pdf(pdf_path: Path, dpi: int = 200) -> list[Path]:
    """Convert PDF pages to images. Returns list of temp image paths."""
    try:
        from pdf2image import convert_from_path
        import tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix="sovai_vision_"))
        images = convert_from_path(str(pdf_path), dpi=dpi, output_folder=str(tmpdir), fmt="png")
        paths = []
        for i, img in enumerate(images):
            p = tmpdir / f"page_{i+1:04d}.png"
            img.save(str(p), "PNG")
            paths.append(p)
        return paths
    except ImportError:
        raise RuntimeError(
            "pdf2image not installed. Run: pip install pdf2image\n"
            "Also ensure poppler is installed: https://github.com/Belval/pdf2image#windows"
        )


def _extract_with_pymupdf(pdf_path: Path) -> str | None:
    """Try to extract text layer from PDF (non-scanned). Returns None if no text."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)
        doc.close()
        if pages:
            return "\n\n--- Page Break ---\n\n".join(pages)
        return None
    except ImportError:
        return None


class VisionTool(Tool):
    name = "vision_analyze"
    description = (
        "Analyze an image or scanned PDF using the vision-language model. "
        "Extracts text, key findings, tables, and handwritten notes. "
        "Supports: .png, .jpg, .jpeg, .bmp, .pdf"
    )
    categories = ["vision", "planning", "general"]
    json_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to image or PDF file",
            },
            "question": {
                "type": "string",
                "description": "Optional specific question to answer about the image",
            },
        },
        "required": ["path"],
    }

    def run(self, path: str, question: str | None = None) -> ToolResult:
        cfg = get_config()
        p = _validate_path(path)
        if p is None:
            return ToolResult.fail(f"Path '{path}' outside workspace.")
        if not p.exists():
            return ToolResult.fail(f"File not found: {path}")

        suffix = p.suffix.lower()
        image_paths: list[Path] = []
        text_layer: str | None = None

        # ── Handle PDF ────────────────────────────────────────────────────
        if suffix == ".pdf":
            # Try text layer first (fast path for non-scanned PDFs)
            text_layer = _extract_with_pymupdf(p)
            if not text_layer:
                # Scanned PDF — rasterize pages
                try:
                    image_paths = _rasterize_pdf(p)
                except RuntimeError as e:
                    return ToolResult.fail(str(e))
        elif suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
            image_paths = [p]
        else:
            return ToolResult.fail(f"Unsupported file type: {suffix}")

        # ── If we got a text layer, use the general model to analyze it ──
        if text_layer and not image_paths:
            prompt = question or "Summarize this document and extract key findings."
            client = ollama.Client(host=cfg.ollama_host)
            try:
                resp = client.chat(
                    model=cfg.model_for("general"),
                    messages=[{
                        "role": "user",
                        "content": f"Document content:\n{text_layer}\n\nTask: {prompt}",
                    }],
                )
                summary = resp.message.content or ""
                return ToolResult.ok({
                    "source": str(p),
                    "method": "text_layer",
                    "raw_text": text_layer[:4000],
                    "summary": summary,
                })
            except Exception as e:
                return ToolResult.fail(str(e))

        # ── Vision model for images ────────────────────────────────────────
        client = ollama.Client(host=cfg.ollama_host)
        page_results = []
        prompt = _VISION_PROMPT
        if question:
            prompt += f"\n\nSpecific question to answer: {question}"

        for img_path in image_paths:
            try:
                resp = client.chat(
                    model=cfg.model_for("vision"),
                    messages=[{
                        "role": "user",
                        "content": prompt,
                        "images": [_image_to_b64(img_path)],
                    }],
                )
                raw_resp = resp.message.content or "{}"

                # Parse JSON from response
                parsed = _parse_vision_json(raw_resp)
                parsed["page"] = img_path.name
                page_results.append(parsed)

            except Exception as e:
                page_results.append({"page": img_path.name, "error": str(e)})

        # Aggregate
        all_text = "\n".join(r.get("raw_text", "") for r in page_results)
        all_findings = []
        for r in page_results:
            all_findings.extend(r.get("key_findings", []))

        return ToolResult.ok({
            "source": str(p),
            "method": "vision_model",
            "pages": len(image_paths),
            "raw_text": all_text,
            "key_findings": all_findings,
            "page_results": page_results,
        })


def _parse_vision_json(raw: str) -> dict:
    """Extract JSON from the vision model response."""
    # Try direct parse
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    # Try extracting JSON block
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Fallback: return raw text
    return {"raw_text": raw, "key_findings": [], "confidence": "low"}

