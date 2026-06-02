from __future__ import annotations

from pathlib import Path
import pdfplumber


def extract_lines_by_page(pdf_path: str | Path) -> list[tuple[int, str]]:
    """Return clean non-empty lines from a text-based PDF as (page_number, line).

    layout=True matters for this city PDF. Without it, pdfplumber can read the name/license
    lines before the address lines and scramble the record order.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    lines: list[tuple[int, str]] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(layout=True, x_tolerance=1, y_tolerance=3) or ""
            for raw_line in text.splitlines():
                line = " ".join(raw_line.strip().split())
                if not line:
                    continue
                if line.startswith("Page "):
                    continue
                if line == "City of Newport News":
                    continue
                if line == "New Business Listing":
                    continue
                if line.startswith("March 2026"):
                    continue
                lines.append((page_number, line))

    return lines
