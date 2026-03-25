"""
PDF Generator — creates study notes PDFs from session content.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger("ai_tutor")


def generate_notes_pdf(
    title: str,
    content_markdown: str,
    key_points: Optional[list] = None,
    formulas: Optional[list] = None,
) -> bytes:
    """
    Generate a PDF from session notes.
    Returns raw PDF bytes.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=20, spaceAfter=20
        )
        heading_style = styles["Heading2"]
        body_style = styles["BodyText"]

        elements = []

        # Title
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))

        # Content (simplified markdown-to-paragraph conversion)
        for line in content_markdown.split("\n"):
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 6))
            elif line.startswith("## "):
                elements.append(Paragraph(line[3:], heading_style))
            elif line.startswith("# "):
                elements.append(Paragraph(line[2:], title_style))
            elif line.startswith("- "):
                elements.append(Paragraph(f"• {line[2:]}", body_style))
            else:
                elements.append(Paragraph(line, body_style))

        # Key Points section
        if key_points:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Key Takeaways", heading_style))
            for i, point in enumerate(key_points, 1):
                elements.append(Paragraph(f"{i}. {point}", body_style))

        # Formulas section
        if formulas:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("Important Formulas", heading_style))
            for formula in formulas:
                elements.append(Paragraph(f"  {formula}", body_style))

        doc.build(elements)
        return buffer.getvalue()

    except ImportError:
        logger.warning("reportlab not available; returning placeholder PDF bytes")
        return b"%PDF-1.4 placeholder"
