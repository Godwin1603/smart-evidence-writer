# utils/pdf_generator.py — Professional police-style PDF report generator
import io
import os
import base64
import logging
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import HexColor, black, white, grey
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage, HRFlowable, KeepTogether
)
from reportlab.lib import colors
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# COLOR THEME
# ─────────────────────────────────────────────────────────
NAVY = HexColor('#1a1f36')
DARK_BLUE = HexColor('#2d3561')
ACCENT_BLUE = HexColor('#3b82f6')
STEEL = HexColor('#64748b')
DARK_BG = HexColor('#0f172a')
LIGHT_BG = HexColor('#f1f5f9')
RED_ALERT = HexColor('#dc2626')
AMBER = HexColor('#f59e0b')
GREEN = HexColor('#22c55e')
WHITE = HexColor('#ffffff')
BORDER_COLOR = HexColor('#334155')

SEVERITY_COLORS = {
    'critical': HexColor('#dc2626'),
    'high': HexColor('#ea580c'),
    'severe': HexColor('#dc2626'),
    'medium': HexColor('#f59e0b'),
    'moderate': HexColor('#f59e0b'),
    'low': HexColor('#22c55e'),
    'minor': HexColor('#22c55e'),
    'none': HexColor('#64748b'),
    'unknown': HexColor('#64748b'),
}


# ─────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────
def _get_styles():
    """Create custom paragraph styles for the report."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'ReportTitle', parent=styles['Title'],
        fontSize=20, textColor=NAVY, spaceAfter=6,
        fontName='Helvetica-Bold', alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        'ReportSubtitle', parent=styles['Normal'],
        fontSize=10, textColor=STEEL, alignment=TA_CENTER,
        spaceAfter=12, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'Classification', parent=styles['Normal'],
        fontSize=11, textColor=RED_ALERT, alignment=TA_CENTER,
        fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=4,
        borderColor=RED_ALERT, borderWidth=1, borderPadding=4
    ))
    styles.add(ParagraphStyle(
        'SectionHeader', parent=styles['Heading2'],
        fontSize=14, textColor=NAVY, spaceBefore=16, spaceAfter=8,
        fontName='Helvetica-Bold', borderColor=ACCENT_BLUE,
        leftIndent=0
    ))
    styles.add(ParagraphStyle(
        'SubSectionHeader', parent=styles['Heading3'],
        fontSize=11, textColor=DARK_BLUE, spaceBefore=10, spaceAfter=6,
        fontName='Helvetica-Bold'
    ))
    # Remove the default BodyText so we can add our custom one
    del styles.byName['BodyText']
    styles.add(ParagraphStyle(
        'BodyText', parent=styles['Normal'],
        fontSize=10, textColor=black, alignment=TA_JUSTIFY,
        spaceAfter=6, fontName='Helvetica', leading=14
    ))
    styles.add(ParagraphStyle(
        'SmallText', parent=styles['Normal'],
        fontSize=8, textColor=STEEL, spaceAfter=4, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'FieldLabel', parent=styles['Normal'],
        fontSize=9, textColor=STEEL, fontName='Helvetica-Bold',
        spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        'FieldValue', parent=styles['Normal'],
        fontSize=10, textColor=black, fontName='Helvetica',
        spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        'AlertText', parent=styles['Normal'],
        fontSize=10, textColor=RED_ALERT, fontName='Helvetica-Bold',
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        'CaptionText', parent=styles['Normal'],
        fontSize=8, textColor=STEEL, fontName='Helvetica-Oblique',
        alignment=TA_CENTER, spaceAfter=8
    ))
    styles.add(ParagraphStyle(
        'FooterText', parent=styles['Normal'],
        fontSize=7, textColor=STEEL, alignment=TA_CENTER,
        fontName='Helvetica'
    ))

    return styles


# ─────────────────────────────────────────────────────────
# MAIN PDF GENERATOR
# ─────────────────────────────────────────────────────────

def generate_pdf(report):
    """
    Generate a professional PDF report from structured report data.
    Returns PDF bytes (in-memory, no disk write).
    """
    buffer = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=25 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
        title=report.get('header', {}).get('report_title', 'Evidence Report'),
        author='Alfa Hawk — Alfa Labs'
    )

    elements = []

    # === COVER / HEADER ===
    elements.extend(_build_pdf_header(report, styles))
    elements.append(Spacer(1, 8))

    # === CASE INFORMATION TABLE ===
    elements.extend(_build_case_info_table(report, styles))
    elements.append(Spacer(1, 10))

    # === EVIDENCE DESCRIPTION ===
    elements.extend(_build_evidence_section(report, styles))
    elements.append(Spacer(1, 6))

    # === EXECUTIVE SUMMARY ===
    elements.append(_section_divider())
    elements.append(Paragraph('1. EXECUTIVE SUMMARY', styles['SectionHeader']))
    elements.append(Paragraph(
        _safe_text(report.get('executive_summary', 'No summary available.')),
        styles['BodyText']
    ))

    # === SCENE DESCRIPTION ===
    if report.get('scene_description'):
        elements.append(Paragraph('2. SCENE DESCRIPTION', styles['SectionHeader']))
        elements.append(Paragraph(_safe_text(report['scene_description']), styles['BodyText']))

    # === DETAILED ANALYSIS ===
    detail_sections = report.get('detailed_analysis', [])
    if detail_sections:
        elements.append(Paragraph('3. DETAILED ANALYSIS', styles['SectionHeader']))
        for sec in detail_sections:
            elements.append(Paragraph(_safe_text(sec.get('title', '')), styles['SubSectionHeader']))
            elements.append(Paragraph(_safe_text(sec.get('content', '')), styles['BodyText']))

    # === VIOLATIONS ===
    violations = report.get('violations', [])
    if violations:
        elements.append(_section_divider())
        elements.append(Paragraph('4. VIOLATIONS DETECTED', styles['SectionHeader']))
        elements.extend(_build_violations_pdf(violations, styles))

    # === ACCIDENTS ===
    accidents = report.get('accidents', [])
    if accidents:
        elements.append(_section_divider())
        elements.append(Paragraph('5. ACCIDENT ANALYSIS', styles['SectionHeader']))
        elements.extend(_build_accidents_pdf(accidents, styles))

    # === PERSONS IDENTIFIED ===
    persons = report.get('persons_identified', [])
    if persons:
        elements.append(_section_divider())
        elements.append(Paragraph('6. PERSONS IDENTIFIED', styles['SectionHeader']))
        elements.extend(_build_persons_pdf(persons, styles))

    # === VEHICLE / NUMBER PLATE REGISTRY ===
    vehicles = report.get('vehicle_registry', [])
    if vehicles:
        elements.append(_section_divider())
        elements.append(Paragraph('7. VEHICLE / NUMBER PLATE REGISTRY', styles['SectionHeader']))
        elements.extend(_build_vehicles_pdf(vehicles, styles))

    # === LANDMARKS ===
    landmarks = report.get('landmarks_locations', [])
    if landmarks:
        elements.append(Paragraph('8. LANDMARKS & LOCATIONS', styles['SectionHeader']))
        elements.extend(_build_landmarks_pdf(landmarks, styles))

    # === TIMELINE ===
    timeline = report.get('timeline', [])
    if timeline:
        elements.append(Paragraph('9. CHRONOLOGICAL TIMELINE', styles['SectionHeader']))
        elements.extend(_build_timeline_pdf(timeline, styles))

    # === RISK ASSESSMENT ===
    risk = report.get('risk_assessment', {})
    if risk:
        elements.append(_section_divider())
        elements.append(Paragraph('10. RISK ASSESSMENT', styles['SectionHeader']))
        elements.extend(_build_risk_pdf(risk, styles))

    # === RECOMMENDATIONS ===
    recs = report.get('investigative_recommendations', [])
    if recs:
        elements.append(Paragraph('11. INVESTIGATIVE RECOMMENDATIONS', styles['SectionHeader']))
        for i, rec in enumerate(recs):
            elements.append(Paragraph(f'{i + 1}. {_safe_text(rec)}', styles['BodyText']))

    # === EVIDENCE EXHIBITS ===
    exhibits = report.get('evidence_exhibits', [])
    if exhibits:
        elements.append(PageBreak())
        elements.append(Paragraph('APPENDIX: EVIDENCE EXHIBITS', styles['SectionHeader']))
        elements.extend(_build_exhibits_pdf(exhibits, styles))

    # === CERTIFICATION ===
    elements.append(PageBreak())
    elements.extend(_build_certification_pdf(report, styles))

    # Build PDF
    try:
        doc.build(elements, onFirstPage=_add_page_border, onLaterPages=_add_page_border)
    except Exception as e:
        logger.error(f"PDF build failed: {e}")
        raise

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ─────────────────────────────────────────────────────────
# PDF SECTION BUILDERS
# ─────────────────────────────────────────────────────────

def _build_pdf_header(report, styles):
    """Build the report header/title section."""
    header = report.get('header', {})
    elements = []

    # Classification banner
    elements.append(Paragraph(
        header.get('classification', 'RESTRICTED'),
        styles['Classification']
    ))
    elements.append(Spacer(1, 6))

    # Title
    elements.append(Paragraph(
        header.get('report_title', 'EVIDENCE ANALYSIS REPORT'),
        styles['ReportTitle']
    ))

    # System name
    elements.append(Paragraph(
        header.get('system_name', 'Alfa Hawk — Alfa Labs'),
        styles['ReportSubtitle']
    ))

    # Divider line
    elements.append(HRFlowable(
        width="100%", thickness=2, color=ACCENT_BLUE,
        spaceAfter=8, spaceBefore=4
    ))

    return elements


def _build_case_info_table(report, styles):
    """Build case information as a styled table."""
    header = report.get('header', {})
    elements = []

    data = [
        ['Case Number:', header.get('case_number', 'N/A'),
         'Report ID:', header.get('report_id', 'N/A')],
        ['Date:', header.get('date', 'N/A'),
         'Time:', header.get('time', 'N/A')],
        ['Officer ID:', header.get('officer_id', 'N/A'),
         'Case Description:', ''],
    ]

    # Add case description spanning full width if present
    case_desc = header.get('case_description', 'N/A')

    table = Table(data, colWidths=[80, 150, 80, 150])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), STEEL),
        ('TEXTCOLOR', (2, 0), (2, -1), STEEL),
        ('TEXTCOLOR', (1, 0), (1, -1), black),
        ('TEXTCOLOR', (3, 0), (3, -1), black),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('BACKGROUND', (2, 0), (2, -1), LIGHT_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)

    if case_desc and case_desc != 'N/A':
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f'<b>Case Description:</b> {_safe_text(case_desc)}', styles['SmallText']))

    return elements


def _build_evidence_section(report, styles):
    """Build evidence description section."""
    elements = []
    evidence = report.get('evidence_description', {})

    elements.append(Paragraph('EVIDENCE FILE DETAILS', styles['SubSectionHeader']))

    data = []
    field_map = [
        ('Filename', 'filename'),
        ('Media Type', 'media_type'),
        ('MIME Type', 'mime_type'),
        ('File Size', 'file_size'),
        ('Dimensions', 'dimensions'),
        ('Duration', 'duration'),
        ('Frame Rate', 'frame_rate'),
        ('Format', 'format'),
        ('Uploaded', 'upload_timestamp'),
    ]

    for label, key in field_map:
        if evidence.get(key):
            data.append([label + ':', str(evidence[key])])

    if data:
        table = Table(data, colWidths=[100, 360])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), STEEL),
            ('TEXTCOLOR', (1, 0), (1, -1), black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, HexColor('#e2e8f0')),
        ]))
        elements.append(table)

    return elements


def _build_violations_pdf(violations, styles):
    """Build violations section in PDF."""
    elements = []

    for v in violations:
        severity = v.get('severity', 'unknown').lower()
        sev_color = SEVERITY_COLORS.get(severity, STEEL)

        # Violation card
        card_data = [
            [Paragraph(f'<b>Violation #{v["index"]}</b>', styles['BodyText']),
             Paragraph(f'<b>Severity:</b> <font color="{sev_color.hexval()}">{severity.upper()}</font>', styles['BodyText'])],
            [Paragraph(f'<b>Type:</b> {_safe_text(v.get("type", ""))}', styles['SmallText']),
             Paragraph(f'<b>Detected at:</b> {v.get("detected_at", "N/A")}', styles['SmallText'])],
        ]

        card_table = Table(card_data, colWidths=[230, 230])
        card_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, sev_color),
            ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(card_table)
        elements.append(Paragraph(_safe_text(v.get('description', '')), styles['BodyText']))

        # Evidence frame if available
        if v.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(v['evidence_frame_base64'], f'Evidence frame for Violation #{v["index"]}', styles))

        elements.append(Spacer(1, 8))

    return elements


def _build_accidents_pdf(accidents, styles):
    """Build accidents section in PDF."""
    elements = []

    for a in accidents:
        severity = a.get('severity', 'unknown').lower()
        sev_color = SEVERITY_COLORS.get(severity, STEEL)

        elements.append(Paragraph(
            f'<b>Accident #{a["index"]}</b> — <font color="{sev_color.hexval()}">{severity.upper()}</font>',
            styles['SubSectionHeader']
        ))
        elements.append(Paragraph(f'<b>Type:</b> {_safe_text(a.get("type", ""))}', styles['BodyText']))
        elements.append(Paragraph(f'<b>Description:</b> {_safe_text(a.get("description", ""))}', styles['BodyText']))
        elements.append(Paragraph(f'<b>Vehicles:</b> {_safe_text(a.get("vehicles_involved", ""))}', styles['BodyText']))
        elements.append(Paragraph(f'<b>Damage:</b> {_safe_text(a.get("damage_assessment", ""))}', styles['BodyText']))

        if a.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(a['evidence_frame_base64'], f'Accident #{a["index"]} evidence', styles))

        elements.append(Spacer(1, 8))

    return elements


def _build_persons_pdf(persons, styles):
    """Build persons identified section."""
    elements = []

    data = [['#', 'ID', 'Description', 'Activity', 'Relevance']]
    for p in persons:
        data.append([
            str(p['index']),
            _safe_text(p.get('person_id', '')),
            _safe_text(p.get('description', ''))[:60],
            _safe_text(p.get('activity', ''))[:40],
            _safe_text(p.get('relevance', '')),
        ])

    if len(data) > 1:
        table = Table(data, colWidths=[25, 60, 180, 120, 75])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(table)

    # Add evidence frames for persons
    for p in persons:
        if p.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(p['evidence_frame_base64'], f'{p.get("person_id", "Person")} — Evidence', styles))

    return elements


def _build_vehicles_pdf(vehicles, styles):
    """Build vehicle registry table."""
    elements = []

    data = [['#', 'Plate Number', 'Vehicle Type', 'Color', 'Region', 'Confidence']]
    for v in vehicles:
        data.append([
            str(v['index']),
            _safe_text(v.get('plate_text', 'N/A')),
            _safe_text(v.get('vehicle_type', '')),
            _safe_text(v.get('vehicle_color', '')),
            _safe_text(v.get('plate_region', '')),
            _safe_text(v.get('confidence', '')),
        ])

    if len(data) > 1:
        table = Table(data, colWidths=[25, 100, 80, 70, 80, 60])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)

    # Add evidence frames for vehicles
    for v in vehicles:
        if v.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(v['evidence_frame_base64'], f'Plate: {v.get("plate_text", "N/A")}', styles))

    return elements


def _build_landmarks_pdf(landmarks, styles):
    """Build landmarks section."""
    elements = []

    for l in landmarks:
        elements.append(Paragraph(
            f'<b>{l["index"]}. {_safe_text(l.get("name", "Unknown"))}</b> ({_safe_text(l.get("type", ""))})',
            styles['BodyText']
        ))
        if l.get('details'):
            elements.append(Paragraph(f'   {_safe_text(l["details"])}', styles['SmallText']))
        if l.get('location_hint'):
            elements.append(Paragraph(f'   Location: {_safe_text(l["location_hint"])}', styles['SmallText']))

    return elements


def _build_timeline_pdf(timeline, styles):
    """Build timeline table."""
    elements = []

    data = [['Seq.', 'Time', 'Event Description']]
    for t in timeline:
        data.append([
            str(t.get('sequence', '')),
            _safe_text(str(t.get('time', ''))),
            _safe_text(str(t.get('event', '')))[:120],
        ])

    if len(data) > 1:
        table = Table(data, colWidths=[35, 70, 355])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(table)

    return elements


def _build_risk_pdf(risk, styles):
    """Build risk assessment section."""
    elements = []

    threat = risk.get('threat_level', 'unknown').lower()
    sev_color = SEVERITY_COLORS.get(threat, STEEL)

    elements.append(Paragraph(
        f'<b>Threat Level:</b> <font color="{sev_color.hexval()}">{threat.upper()}</font>',
        styles['BodyText']
    ))
    if risk.get('risk_factors'):
        elements.append(Paragraph(f'<b>Risk Factors:</b> {_safe_text(risk["risk_factors"])}', styles['BodyText']))
    if risk.get('recommended_response'):
        elements.append(Paragraph(f'<b>Recommended Response:</b> {_safe_text(risk["recommended_response"])}', styles['BodyText']))

    return elements


def _build_exhibits_pdf(exhibits, styles):
    """Build evidence exhibits gallery in PDF."""
    elements = []

    key_findings = [e for e in exhibits if e.get('is_key_finding')]
    other_frames = [e for e in exhibits if not e.get('is_key_finding')]

    if key_findings:
        elements.append(Paragraph('Key Finding Frames', styles['SubSectionHeader']))
        for exhibit in key_findings:
            elements.extend(_embed_frame_image(
                exhibit.get('base64', ''),
                f'[KEY] {exhibit.get("timestamp", "")} — {exhibit.get("description", "")}',
                styles,
                max_width=4 * inch
            ))

    if other_frames:
        elements.append(Paragraph('Additional Evidence Frames', styles['SubSectionHeader']))
        # Display in a grid (2 per row)
        row = []
        for exhibit in other_frames:
            img = _get_rl_image(exhibit.get('base64', ''), max_width=2.8 * inch)
            if img:
                caption = Paragraph(
                    f'{exhibit.get("timestamp", "")}',
                    styles['CaptionText']
                )
                row.append([img, caption])

            if len(row) == 2:
                # Create 2-column table
                table_data = [[row[0][0], row[1][0]], [row[0][1], row[1][1]]]
                t = Table(table_data, colWidths=[3 * inch, 3 * inch])
                t.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(t)
                row = []

        # Handle remaining odd frame
        if row:
            elements.append(row[0][0])
            elements.append(row[0][1])

    return elements


def _build_certification_pdf(report, styles):
    """Build certification and signature section."""
    elements = []
    cert = report.get('certification', {})

    elements.append(Paragraph('REPORT CERTIFICATION', styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph(_safe_text(cert.get('disclaimer', '')), styles['BodyText']))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f'<b>Generated by:</b> {_safe_text(cert.get("system", ""))}',
        styles['SmallText']
    ))
    elements.append(Paragraph(
        f'<b>Generated at:</b> {cert.get("generated_at", "")}',
        styles['SmallText']
    ))
    elements.append(Paragraph(
        f'<b>Confidence Score:</b> {report.get("confidence_score", 0):.0%}',
        styles['SmallText']
    ))

    elements.append(Spacer(1, 20))

    # Signature blocks
    sig_blocks = cert.get('signature_blocks', [])
    if sig_blocks:
        for sig in sig_blocks:
            elements.append(Spacer(1, 16))
            elements.append(Paragraph(f'<b>{sig.get("title", "")}</b>', styles['BodyText']))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f'Name: {sig.get("name", "_" * 30)}', styles['SmallText']))
            elements.append(Paragraph(f'Rank: {sig.get("rank", "_" * 30)}', styles['SmallText']))
            elements.append(Paragraph(f'Badge/ID: {sig.get("badge", "_" * 30)}', styles['SmallText']))
            elements.append(Paragraph(f'Date: {sig.get("date", "_" * 30)}', styles['SmallText']))

    return elements


# ─────────────────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────────────────

def _safe_text(text):
    """Escape XML special characters for ReportLab paragraphs."""
    if not text:
        return ''
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def _section_divider():
    """Create a thin horizontal divider."""
    return HRFlowable(
        width="100%", thickness=0.5, color=HexColor('#e2e8f0'),
        spaceBefore=8, spaceAfter=4
    )


def _embed_frame_image(base64_str, caption, styles, max_width=3.5 * inch):
    """Embed a base64 image in the PDF with a caption."""
    elements = []
    img = _get_rl_image(base64_str, max_width)
    if img:
        elements.append(img)
        elements.append(Paragraph(_safe_text(caption), styles['CaptionText']))
        elements.append(Spacer(1, 6))
    return elements


def _get_rl_image(base64_str, max_width=3.5 * inch):
    """Convert base64 string to a ReportLab Image object."""
    if not base64_str:
        return None
    try:
        img_data = base64.b64decode(base64_str)
        img_buf = io.BytesIO(img_data)

        # Get original dimensions
        pil_img = PILImage.open(io.BytesIO(img_data))
        orig_w, orig_h = pil_img.size

        # Scale to fit max_width while preserving aspect ratio
        max_height = 3 * inch
        scale = min(max_width / orig_w, max_height / orig_h, 1.0)
        display_w = orig_w * scale
        display_h = orig_h * scale

        return RLImage(img_buf, width=display_w, height=display_h)
    except Exception as e:
        logger.warning(f"Could not embed image: {e}")
        return None


def _add_page_border(canvas_obj, doc):
    """Add page border, header, and footer to each page."""
    canvas_obj.saveState()

    # Page border
    canvas_obj.setStrokeColor(BORDER_COLOR)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.rect(
        12 * mm, 12 * mm,
        A4[0] - 24 * mm, A4[1] - 24 * mm
    )

    # Footer
    canvas_obj.setFont('Helvetica', 7)
    canvas_obj.setFillColor(STEEL)
    canvas_obj.drawCentredString(
        A4[0] / 2, 15 * mm,
        f'Alfa Hawk \u2014 Alfa Labs \u2014 Confidential \u2014 Page {canvas_obj.getPageNumber()}'
    )

    # Top-right classification mark
    canvas_obj.setFont('Helvetica-Bold', 7)
    canvas_obj.setFillColor(RED_ALERT)
    canvas_obj.drawRightString(A4[0] - 15 * mm, A4[1] - 10 * mm, 'RESTRICTED')

    canvas_obj.restoreState()