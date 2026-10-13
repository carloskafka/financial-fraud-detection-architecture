#!/usr/bin/env python3
"""Render the Markdown architecture report and diagrams to a PDF."""

from __future__ import annotations

import argparse
from html import escape
from html.parser import HTMLParser
from pathlib import Path

import markdown
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "architecture-report.md"
OUTPUT = ROOT / "architecture-report.pdf"
PAGE_WIDTH, PAGE_HEIGHT = letter
FONT_DIR = Path("/System/Library/Fonts/Supplemental")


class Element:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []


class TreeParser(HTMLParser):
    VOID_TAGS = {"br", "hr", "img"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in self.VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Element(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def register_fonts():
    regular = FONT_DIR / "Arial.ttf"
    bold = FONT_DIR / "Arial Bold.ttf"
    italic = FONT_DIR / "Arial Italic.ttf"
    bold_italic = FONT_DIR / "Arial Bold Italic.ttf"
    if all(path.exists() for path in (regular, bold, italic, bold_italic)):
        pdfmetrics.registerFont(TTFont("ReportArial", str(regular)))
        pdfmetrics.registerFont(TTFont("ReportArial-Bold", str(bold)))
        pdfmetrics.registerFont(TTFont("ReportArial-Italic", str(italic)))
        pdfmetrics.registerFont(
            TTFont("ReportArial-BoldItalic", str(bold_italic))
        )
        pdfmetrics.registerFontFamily(
            "ReportArial",
            normal="ReportArial",
            bold="ReportArial-Bold",
            italic="ReportArial-Italic",
            boldItalic="ReportArial-BoldItalic",
        )
        return "ReportArial"
    return "Helvetica"


def inline_markup(node):
    if isinstance(node, str):
        return escape(node, quote=False)

    tag = node.tag
    body = "".join(inline_markup(child) for child in node.children)
    if tag == "strong" or tag == "b":
        return f"<b>{body}</b>"
    if tag == "em" or tag == "i":
        return f"<i>{body}</i>"
    if tag == "code":
        return f'<font name="Courier" backColor="#eef2f7">{body}</font>'
    if tag == "a":
        href = escape(node.attrs.get("href", ""), quote=True)
        return f'<link href="{href}" color="#1558a6">{body}</link>'
    if tag == "br":
        return "<br/>"
    return body


def text_content(node):
    if isinstance(node, str):
        return node
    return "".join(text_content(child) for child in node.children)


def make_styles(font_name):
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=f"{font_name}-Bold",
            fontSize=27,
            leading=32,
            textColor=colors.HexColor("#12304a"),
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=font_name,
            fontSize=12,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#526477"),
        ),
        "h1": ParagraphStyle(
            "ReportH1",
            parent=base["Heading1"],
            fontName=f"{font_name}-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#12304a"),
            spaceBefore=16,
            spaceAfter=9,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "ReportH2",
            parent=base["Heading2"],
            fontName=f"{font_name}-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1d557a"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "ReportH3",
            parent=base["Heading3"],
            fontName=f"{font_name}-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1d557a"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8.6,
            leading=12.2,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#182230"),
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "ReportBullet",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8.4,
            leading=11.5,
            textColor=colors.HexColor("#182230"),
            spaceAfter=2,
        ),
        "table": ParagraphStyle(
            "ReportTable",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=7.1,
            leading=9,
            textColor=colors.HexColor("#182230"),
            spaceAfter=0,
        ),
        "table_head": ParagraphStyle(
            "ReportTableHead",
            parent=base["BodyText"],
            fontName=f"{font_name}-Bold",
            fontSize=7.2,
            leading=9,
            textColor=colors.white,
            spaceAfter=0,
        ),
        "code": ParagraphStyle(
            "ReportCode",
            fontName="Courier",
            fontSize=7.2,
            leading=9,
            leftIndent=8,
            rightIndent=8,
            borderColor=colors.HexColor("#d8e0e8"),
            borderWidth=0.5,
            borderPadding=6,
            backColor=colors.HexColor("#f5f7fa"),
            spaceBefore=4,
            spaceAfter=8,
        ),
    }
    return styles


def build_list(element, styles):
    items = []
    for child in element.children:
        if not isinstance(child, Element) or child.tag != "li":
            continue
        blocks = []
        for block in child.children:
            if isinstance(block, Element) and block.tag in {"ul", "ol"}:
                blocks.append(build_list(block, styles))
            elif isinstance(block, Element) and block.tag == "p":
                blocks.append(Paragraph(inline_markup(block), styles["bullet"]))
            elif isinstance(block, str) and block.strip():
                blocks.append(Paragraph(escape(block.strip()), styles["bullet"]))
        if not blocks:
            blocks = [Paragraph(inline_markup(child), styles["bullet"])]
        items.append(ListItem(blocks, leftIndent=12, bulletColor=colors.HexColor("#1d557a")))
    return ListFlowable(
        items,
        bulletType="1" if element.tag == "ol" else "bullet",
        start="1",
        leftIndent=18,
        bulletFontName="Helvetica",
        bulletFontSize=7,
        spaceBefore=2,
        spaceAfter=6,
    )


def build_table(element, styles, available_width):
    rows = []
    for row in element.children:
        if not isinstance(row, Element) or row.tag not in {"thead", "tbody", "tr"}:
            continue
        row_nodes = row.children if row.tag in {"thead", "tbody"} else [row]
        for row_node in row_nodes:
            if not isinstance(row_node, Element) or row_node.tag != "tr":
                continue
            cells = []
            for cell in row_node.children:
                if isinstance(cell, Element) and cell.tag in {"th", "td"}:
                    style = styles["table_head"] if cell.tag == "th" else styles["table"]
                    cells.append(Paragraph(inline_markup(cell), style))
            if cells:
                rows.append(cells)
    if not rows:
        return None

    column_count = max(len(row) for row in rows)
    column_widths = [available_width / column_count] * column_count
    table = Table(rows, colWidths=column_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d557a")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c7d0d9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#f5f7fa"),
                ]),
            ]
        )
    )
    return table


def convert_block(element, styles, available_width):
    tag = element.tag
    if tag in {"h1", "h2", "h3"}:
        return Paragraph(inline_markup(element), styles[tag])
    if tag == "p":
        image = next(
            (
                child
                for child in element.children
                if isinstance(child, Element) and child.tag == "img"
            ),
            None,
        )
        if image:
            path = (ROOT / image.attrs["src"]).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Report image not found: {path}")
            rendered = Image(str(path))
            max_height = PAGE_HEIGHT - 2.0 * inch
            scale = min(
                available_width / rendered.imageWidth,
                max_height / rendered.imageHeight,
            )
            rendered.drawWidth = rendered.imageWidth * scale
            rendered.drawHeight = rendered.imageHeight * scale
            return KeepTogether([rendered, Spacer(1, 6)])
        return Paragraph(inline_markup(element), styles["body"])
    if tag in {"ul", "ol"}:
        return build_list(element, styles)
    if tag == "pre":
        return Preformatted(text_content(element), styles["code"], maxLineLength=100)
    if tag == "table":
        return build_table(element, styles, available_width)
    if tag == "blockquote":
        quote_style = ParagraphStyle(
            "ReportQuote",
            parent=styles["body"],
            leftIndent=12,
            borderColor=colors.HexColor("#91a8bc"),
            borderWidth=2,
            borderPadding=6,
        )
        return Paragraph(inline_markup(element), quote_style)
    if tag == "hr":
        return Spacer(1, 8)
    return None


def draw_page(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d8e0e8"))
    canvas.line(
        document.leftMargin,
        0.55 * inch,
        PAGE_WIDTH - document.rightMargin,
        0.55 * inch,
    )
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#526477"))
    canvas.drawString(document.leftMargin, 0.36 * inch, "Real-Time Financial Fraud Detection")
    canvas.drawRightString(
        PAGE_WIDTH - document.rightMargin,
        0.36 * inch,
        f"Page {document.page}",
    )
    canvas.restoreState()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    font_name = register_fonts()
    styles = make_styles(font_name)
    source = REPORT.read_text(encoding="utf-8")
    rendered_html = markdown.markdown(
        source,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    tree_parser = TreeParser()
    tree_parser.feed(rendered_html)

    title = next(
        (
            text_content(child)
            for child in tree_parser.root.children
            if isinstance(child, Element) and child.tag == "h1"
        ),
        "Architecture Report",
    )
    document = SimpleDocTemplate(
        str(args.output),
        pagesize=letter,
        rightMargin=0.62 * inch,
        leftMargin=0.62 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.78 * inch,
        title=title,
        author="Architecture Design",
        subject="Real-time financial fraud detection architecture",
    )
    available_width = PAGE_WIDTH - document.leftMargin - document.rightMargin
    story = [
        Spacer(1, 1.7 * inch),
        Paragraph(escape(title), styles["title"]),
        Paragraph("Solution Architecture Report", styles["subtitle"]),
        Spacer(1, 0.22 * inch),
        Paragraph("Version 1.0 • Proposed reference architecture", styles["subtitle"]),
        Spacer(1, 2.0 * inch),
        Paragraph(
            "Real-time transaction analysis • durable replay • analyst alerting • "
            "operational observability",
            styles["subtitle"],
        ),
        PageBreak(),
    ]

    skipped_title = False
    for child in tree_parser.root.children:
        if isinstance(child, str):
            continue
        if child.tag == "h1" and not skipped_title:
            skipped_title = True
            continue
        block = convert_block(child, styles, available_width)
        if block is not None:
            story.append(block)
            if child.tag in {"h1", "h2", "h3", "p", "table", "pre"}:
                story.append(Spacer(1, 3))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
