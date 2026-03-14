# reporting/pdf_generator.py — V2 Professional forensic PDF report generator (India Edition)
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

from backend.reporting.hash_utils import PDF_CREATOR, PDF_PRODUCER, PLATFORM_NAME, PLATFORM_VERSION
from backend.reporting.watermark import apply_page_watermarks

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
LEGAL_BG = HexColor('#fef3c7')
LEGAL_BORDER = HexColor('#d97706')

SEVERITY_COLORS = {
    'critical': HexColor('#dc2626'),
    'high': HexColor('#ea580c'),
    'severe': HexColor('#dc2626'),
    'fatal': HexColor('#dc2626'),
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
    styles.add(ParagraphStyle(
        'DisclaimerText', parent=styles['Normal'],
        fontSize=9, textColor=HexColor('#92400e'), fontName='Helvetica-Oblique',
        spaceAfter=6, alignment=TA_JUSTIFY, leading=12
    ))
    styles.add(ParagraphStyle(
        'HashText', parent=styles['Normal'],
        fontSize=7, textColor=STEEL, fontName='Courier',
        spaceAfter=4
    ))

    return styles


# ─────────────────────────────────────────────────────────
# MAIN PDF GENERATOR — V2 INVESTIGATOR-FRIENDLY ORDER
# ─────────────────────────────────────────────────────────

def generate_pdf(report):
    """
    V2: Generate a professional forensic PDF report.
    Returns PDF bytes (in-memory, no disk write).
    """
    buffer = io.BytesIO()
    styles = _get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=25 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
        title=report.get('header', {}).get('report_title', 'Evidence Report'),
        author='Alfa Hawk — AI Forensic Evidence Report Generator | Alfa Labs, a child company of Alfa Groups'
    )

    elements = []
    section_num = 0

    def next_section():
        nonlocal section_num
        section_num += 1
        return section_num

    # === COVER / HEADER ===
    elements.extend(_build_pdf_header(report, styles))
    elements.append(Spacer(1, 8))

    # === CASE INFORMATION TABLE ===
    elements.extend(_build_case_info_table(report, styles))
    elements.append(Spacer(1, 10))

    # === EVIDENCE DESCRIPTION ===
    elements.extend(_build_evidence_section(report, styles))
    elements.append(Spacer(1, 6))

    # === 1. EXECUTIVE SUMMARY ===
    elements.append(_section_divider())
    n = next_section()
    elements.append(Paragraph(f'{n}. EXECUTIVE SUMMARY', styles['SectionHeader']))
    elements.append(Paragraph(
        _safe_text(report.get('executive_summary', 'No summary available.')),
        styles['BodyText']
    ))

    # === 2. KEY EVIDENCE OBSERVATIONS (V2.1) ===
    observations = report.get('key_evidence_observations', [])
    if observations:
        elements.append(Paragraph('KEY EVIDENCE OBSERVATIONS', styles['SubSectionHeader']))
        for obs in observations:
            elements.append(Paragraph(f'\u2022 {_safe_text(obs)}', styles['BodyText']))
        elements.append(Spacer(1, 6))

    # === 3. EVIDENCE INTEGRITY (V2) ===
    integrity = report.get('evidence_integrity', {})
    if integrity:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. EVIDENCE INTEGRITY', styles['SectionHeader']))
        elements.extend(_build_integrity_pdf(integrity, styles))

    # === 4. VIDEO QUALITY ASSESSMENT (V2.1) ===
    quality = report.get('video_quality_assessment', {})
    if quality:
        n = next_section()
        elements.append(Paragraph(f'{n}. VIDEO QUALITY ASSESSMENT', styles['SectionHeader']))
        elements.extend(_build_video_quality_pdf(quality, styles))

    # === 5. SCENE DESCRIPTION ===
    if report.get('scene_description'):
        n = next_section()
        elements.append(Paragraph(f'{n}. SCENE DESCRIPTION', styles['SectionHeader']))
        scene = report['scene_description']
        env = scene.get('environment', '') if isinstance(scene, dict) else scene
        elements.append(Paragraph(_safe_text(env), styles['BodyText']))
        
        # Camera Context
        if isinstance(scene, dict) and scene.get('camera_context'):
            elements.append(Paragraph('Camera Perspective:', styles['SubSectionHeader']))
            cc = scene['camera_context']
            cc_text = f"<b>Position:</b> {cc.get('camera_position', 'N/A')}<br/>"
            cc_text += f"<b>Field of View:</b> {cc.get('field_of_view', 'N/A')}<br/>"
            cc_text += f"<b>Limitations:</b> {cc.get('visibility_limitations', 'N/A')}"
            elements.append(Paragraph(cc_text, styles['BodyText']))

    # === 4. INCIDENT RECONSTRUCTION (V2) ===
    phases = report.get('incident_phases', [])
    if phases:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. INCIDENT RECONSTRUCTION', styles['SectionHeader']))
        elements.extend(_build_phases_pdf(phases, styles))

    # === 5. PERSONS OF INTEREST (V2) ===
    persons = report.get('persons_identified', [])
    if persons:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. PERSONS OF INTEREST', styles['SectionHeader']))
        elements.extend(_build_persons_v2_pdf(persons, styles))

    # === 6. WEAPONS & OBJECTS (V2) ===
    weapons = report.get('weapons_objects', [])
    if weapons:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. WEAPONS &amp; OBJECTS DETECTED', styles['SectionHeader']))
        elements.extend(_build_weapons_pdf(weapons, styles))

    # === 7. LEGAL CLASSIFICATION (V2) ===
    legal = report.get('legal_classification', {})
    if legal and legal.get('classifications'):
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. LEGAL CLASSIFICATION (INDICATIVE)', styles['SectionHeader']))
        elements.extend(_build_legal_pdf(legal, styles))

    # === 8. VIOLATIONS ===
    violations = report.get('violations', [])
    if violations:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. VIOLATIONS DETECTED', styles['SectionHeader']))
        elements.extend(_build_violations_pdf(violations, styles))

    # === 9. ACCIDENTS ===
    accidents = report.get('accidents', [])
    if accidents:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. ACCIDENT ANALYSIS', styles['SectionHeader']))
        elements.extend(_build_accidents_pdf(accidents, styles))

    # === 10. CHRONOLOGICAL TIMELINE ===
    timeline = report.get('timeline', [])
    if timeline:
        n = next_section()
        elements.append(Paragraph(f'{n}. CHRONOLOGICAL TIMELINE', styles['SectionHeader']))
        elements.extend(_build_timeline_pdf(timeline, styles))

    # === 11. VEHICLE REGISTRY ===
    vehicles = report.get('vehicle_registry', [])
    if vehicles:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. VEHICLE / NUMBER PLATE REGISTRY', styles['SectionHeader']))
        elements.extend(_build_vehicles_pdf(vehicles, styles))

    # === 12. RISK ASSESSMENT ===
    risk = report.get('risk_assessment', {})
    if risk and risk.get('threat_level'):
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. RISK &amp; THREAT ASSESSMENT', styles['SectionHeader']))
        elements.extend(_build_risk_pdf(risk, styles))

    # === 13. RECOMMENDATIONS ===
    recs = report.get('investigative_recommendations', [])
    if recs:
        n = next_section()
        elements.append(Paragraph(f'{n}. INVESTIGATIVE LEADS', styles['SectionHeader']))
        for i, rec in enumerate(recs):
            elements.append(Paragraph(f'{i + 1}. {_safe_text(rec)}', styles['BodyText']))

    # === 14. AI CONFIDENCE MATRIX (V2) ===
    conf_matrix = report.get('confidence_matrix', {})
    if conf_matrix:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. AI CONFIDENCE MATRIX', styles['SectionHeader']))
        elements.extend(_build_confidence_matrix_pdf(conf_matrix, styles))

    # === 15. AI LIMITATIONS (V2) ===
    limitations = report.get('ai_limitations', [])
    if limitations:
        n = next_section()
        elements.append(Paragraph(f'{n}. AI ANALYSIS LIMITATIONS', styles['SectionHeader']))
        for lim in limitations:
            elements.append(Paragraph(f'\u2022 {_safe_text(lim)}', styles['BodyText']))

    # === 16. AI PROCESSING DISCLOSURE (V2) ===
    disclosure = report.get('ai_processing_disclosure', '')
    if disclosure:
        n = next_section()
        elements.append(_section_divider())
        elements.append(Paragraph(f'{n}. AI PROCESSING DISCLOSURE', styles['SectionHeader']))
        elements.append(Paragraph(_safe_text(disclosure), styles['BodyText']))

    # === 17. CHAIN OF PROCESSING (V2) ===
    chain = report.get('chain_of_processing', {})
    if chain:
        n = next_section()
        elements.append(Paragraph(f'{n}. EVIDENCE HANDLING &amp; CHAIN OF PROCESSING', styles['SectionHeader']))
        elements.extend(_build_chain_pdf(chain, styles))

    # === EVIDENCE EXHIBITS ===
    exhibits = report.get('evidence_exhibits', [])
    if exhibits:
        elements.append(PageBreak())
        elements.append(Paragraph('APPENDIX A: EVIDENCE EXHIBITS', styles['SectionHeader']))
        elements.extend(_build_exhibits_pdf(exhibits, styles))

    # === EVIDENCE FRAME INDEX (V2) ===
    frame_index = report.get('evidence_frame_index', [])
    if frame_index:
        elements.append(Paragraph('APPENDIX B: EVIDENCE FRAME INDEX', styles['SubSectionHeader']))
        elements.extend(_build_frame_index_pdf(frame_index, styles))

    # === CERTIFICATION ===
    elements.append(PageBreak())
    elements.extend(_build_certification_pdf(report, styles))

    # Build PDF
    try:
        # Pass report info to border function using doc attributes
        doc.report_id = report.get('header', {}).get('report_id', 'N/A')
        doc.report_hash = report.get('report_integrity_hash', 'N/A')
        doc.generated_at = report.get('certification', {}).get('generated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        doc.generated_at_iso = report.get('generated_at', datetime.now().isoformat())
        doc.platform_name = report.get('platform_verification', {}).get('platform_name', PLATFORM_NAME)
        doc.platform_version = report.get('platform_verification', {}).get('platform_version', PLATFORM_VERSION)
        doc.pdf_creator = PDF_CREATOR
        doc.pdf_producer = PDF_PRODUCER

        doc.build(elements, onFirstPage=_add_page_border, onLaterPages=_add_page_border)
        
        # After build, we can't easily add metadata to the buffer unless we use a wrapper
        # or set it on the canvas during doc.build. 
        # Actually, doc.build uses Canvas. We can set it in _add_page_border.
    except Exception as e:
        logger.error(f"PDF build failed: {e}")
        raise

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ─────────────────────────────────────────────────────────
# PDF SECTION BUILDERS — EXISTING (updated)
# ─────────────────────────────────────────────────────────

def _build_pdf_header(report, styles):
    header = report.get('header', {})
    elements = []
    elements.append(Paragraph(
        header.get('classification', 'RESTRICTED'),
        styles['Classification']
    ))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        header.get('report_title', 'EVIDENCE ANALYSIS REPORT'),
        styles['ReportTitle']
    ))
    elements.append(Paragraph(
        header.get('system_name', 'Alfa Hawk — Alfa Labs'),
        styles['ReportSubtitle']
    ))
    elements.append(HRFlowable(
        width="100%", thickness=2, color=ACCENT_BLUE,
        spaceAfter=8, spaceBefore=4
    ))
    return elements


def _build_case_info_table(report, styles):
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
    elements = []
    evidence = report.get('evidence_description', {})
    elements.append(Paragraph('EVIDENCE FILE DETAILS', styles['SubSectionHeader']))
    data = []
    field_map = [
        ('Filename', 'filename'), ('Media Type', 'media_type'),
        ('MIME Type', 'mime_type'), ('File Size', 'file_size'),
        ('Dimensions', 'dimensions'), ('Duration', 'duration'),
        ('Frame Rate', 'frame_rate'), ('Format', 'format'),
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
    elements = []
    for v in violations:
        severity = v.get('severity', 'unknown').lower()
        sev_color = SEVERITY_COLORS.get(severity, STEEL)
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
        elements.append(Paragraph(f"<b>Observed Action:</b> {_safe_text(v.get('observed_action', v.get('description', '')))}", styles['BodyText']))
        elements.append(Paragraph(_safe_text(v.get('description', '')), styles['BodyText']))
        if v.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(v['evidence_frame_base64'],
                f'Evidence frame for Violation #{v["index"]}', styles))
        elements.append(Spacer(1, 8))
    return elements


def _build_accidents_pdf(accidents, styles):
    elements = []
    for a in accidents:
        severity = a.get('severity', 'unknown').lower()
        sev_color = SEVERITY_COLORS.get(severity, STEEL)
        elements.append(Paragraph(
            f'<b>Accident #{a["index"]}</b> \u2014 <font color="{sev_color.hexval()}">{severity.upper()}</font>',
            styles['SubSectionHeader']
        ))
        elements.append(Paragraph(f'<b>Type:</b> {_safe_text(a.get("type", ""))}', styles['BodyText']))
        elements.append(Paragraph(f'<b>Description:</b> {_safe_text(a.get("description", ""))}', styles['BodyText']))
        elements.append(Paragraph(f'<b>Vehicles:</b> {_safe_text(a.get("vehicles_involved", ""))}', styles['BodyText']))
        elements.append(Paragraph(f'<b>Damage:</b> {_safe_text(a.get("damage_assessment", ""))}', styles['BodyText']))
        if a.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(a['evidence_frame_base64'],
                f'Accident #{a["index"]} evidence', styles))
        elements.append(Spacer(1, 8))
    return elements


def _build_vehicles_pdf(vehicles, styles):
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
    for v in vehicles:
        if v.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(v['evidence_frame_base64'],
                f'Plate: {v.get("plate_text", "N/A")}', styles))
    return elements


def _build_timeline_pdf(timeline, styles):
    elements = []
    data = [['Seq.', 'Time', 'Event Description']]
    for t in timeline:
        data.append([
            str(t.get('sequence', '')),
            _safe_text(str(t.get('time', ''))),
            _safe_text(str(t.get('event', ''))),
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
    elements = []
    threat = risk.get('threat_level', 'unknown').lower()
    sev_color = SEVERITY_COLORS.get(threat, STEEL)
    elements.append(Paragraph(
        f'<b>Threat Level:</b> <font color="{sev_color.hexval()}">{threat.upper()}</font>',
        styles['BodyText']
    ))
    if risk.get('risk_factors'):
        elements.append(Paragraph(f'<b>Risk Factors:</b> {_safe_text(risk["risk_factors"])}', styles['BodyText']))
    if risk.get('justification'):
        elements.append(Paragraph(f'<b>Justification:</b> {_safe_text(risk["justification"])}', styles['BodyText']))
    if risk.get('recommended_response'):
        elements.append(Paragraph(f'<b>Recommended Response:</b> {_safe_text(risk["recommended_response"])}', styles['BodyText']))
    return elements


def _build_exhibits_pdf(exhibits, styles):
    elements = []
    key_findings = [e for e in exhibits if e.get('is_key_finding')]
    other_frames = [e for e in exhibits if not e.get('is_key_finding')]
    if key_findings:
        elements.append(Paragraph('Key Finding Frames', styles['SubSectionHeader']))
        for exhibit in key_findings:
            elements.extend(_embed_frame_image(
                exhibit.get('base64', ''),
                f'[KEY] {exhibit.get("timestamp", "")} \u2014 {exhibit.get("description", "")}',
                styles, max_width=4 * inch
            ))
    if other_frames:
        elements.append(Paragraph('Additional Evidence Frames', styles['SubSectionHeader']))
        row = []
        for exhibit in other_frames:
            img = _get_rl_image(exhibit.get('base64', ''), max_width=2.8 * inch)
            if img:
                caption = Paragraph(f'{exhibit.get("timestamp", "")}', styles['CaptionText'])
                row.append([img, caption])
            if len(row) == 2:
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
        if row:
            elements.append(row[0][0])
            elements.append(row[0][1])
    return elements


def _build_certification_pdf(report, styles):
    elements = []
    cert = report.get('certification', {})
    integrity = report.get('evidence_integrity', {})
    verification = report.get('platform_verification', {})
    elements.append(Paragraph('REPORT CERTIFICATION', styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(_safe_text(cert.get('disclaimer', '')), styles['BodyText']))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f'<b>Generated by:</b> {_safe_text(cert.get("system", ""))}', styles['SmallText']))
    elements.append(Paragraph(
        f'<b>Generated at:</b> {cert.get("generated_at", "")}', styles['SmallText']))
    elements.append(Paragraph(
        f'<b>Platform:</b> {_safe_text(verification.get("platform_name", PLATFORM_NAME))}', styles['SmallText']))
    elements.append(Paragraph(
        f'<b>Platform Version:</b> {_safe_text(verification.get("platform_version", PLATFORM_VERSION))}', styles['SmallText']))
    evidence_hash = integrity.get('sha256', '')
    if evidence_hash:
        elements.append(Paragraph('<b>Evidence Hash (SHA-256):</b>', styles['SmallText']))
        elements.append(Paragraph(evidence_hash, styles['HashText']))
    elements.append(Paragraph(
        f'<b>Confidence Score:</b> {report.get("confidence_score", 0):.0%}', styles['SmallText']))

    # V2: Report Integrity Hash
    report_hash = report.get('report_integrity_hash', '')
    if report_hash:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph('<b>Report Integrity Hash (SHA-256):</b>', styles['SmallText']))
        elements.append(Paragraph(report_hash, styles['HashText']))

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
# V2 NEW PDF SECTION BUILDERS
# ─────────────────────────────────────────────────────────

def _build_integrity_pdf(integrity, styles):
    """Build evidence integrity section in PDF."""
    elements = []
    data = []
    field_map = [
        ('SHA-256 Hash', 'sha256'),
        ('File Size', 'file_size_mb'),
        ('Media Format', 'media_format'),
        ('Resolution', 'resolution'),
        ('Frame Rate', 'frame_rate'),
        ('Duration', 'duration'),
        ('Codec', 'codec'),
        ('Processing Timestamp', 'processing_timestamp'),
    ]
    for label, key in field_map:
        val = integrity.get(key)
        if val is not None and val != 0:
            display = f'{val} MB' if key == 'file_size_mb' else str(val)
            data.append([label + ':', display])
    if data:
        table = Table(data, colWidths=[130, 330])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Courier' if 'sha256' in [d[0] for d in data] else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), STEEL),
            ('TEXTCOLOR', (1, 0), (1, -1), black),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 1, ACCENT_BLUE),
        ]))
        elements.append(table)
    return elements


def _build_phases_pdf(phases, styles):
    """Build incident reconstruction phases table."""
    elements = []
    data = [['Phase', 'Description', 'Time Range', 'Severity', 'Evidence']]
    for p in phases:
        severity = p.get('severity', 'low').lower()
        sev_color = SEVERITY_COLORS.get(severity, STEEL)
        data.append([
            str(p.get('phase', '')),
            Paragraph(_safe_text(p.get('description', '')), styles['SmallText']),
            _safe_text(p.get('time_range', 'N/A')),
            Paragraph(f'<font color="{sev_color.hexval()}">{severity.upper()}</font>', styles['SmallText']),
            _safe_text(p.get('evidence_frame', 'N/A')),
        ])
    if len(data) > 1:
        table = Table(data, colWidths=[35, 200, 90, 65, 55])
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
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(table)
    return elements


def _build_video_quality_pdf(quality, styles):
    """Build video quality assessment section for PDF."""
    elements = []
    data = [
        ['Resolution Rating:', quality.get('resolution', 'N/A')],
        ['Lighting Quality:', quality.get('lighting', 'N/A')],
        ['Motion Blur:', quality.get('motion_blur', 'N/A')],
        ['ID Reliability:', quality.get('identification_reliability', 'N/A')],
    ]
    table = Table(data, colWidths=[130, 330])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), STEEL),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, HexColor('#e2e8f0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 6))
    return elements


def _build_persons_v2_pdf(persons, styles):
    """Build V2 persons of interest section with P-ID system."""
    elements = []
    data = [['P-ID', 'Description', 'Observed Role', 'Visibility', 'Seen', 'Actions']]
    for p in persons:
        actions = p.get('actions', [])
        if isinstance(actions, list):
            actions_str = '; '.join(actions[:3])
        else:
            actions_str = str(actions)

        data.append([
            _safe_text(p.get('person_id', '')),
            Paragraph(_safe_text(p.get('description', ''))[:80], styles['SmallText']),
            _safe_text(p.get('observed_role', p.get('role', 'Unknown'))),
            _safe_text(p.get('visibility_confidence', 'N/A')),
            _safe_text(p.get('first_seen', 'N/A')),
            Paragraph(_safe_text(actions_str)[:70], styles['SmallText']),
        ])
    if len(data) > 1:
        table = Table(data, colWidths=[35, 120, 75, 55, 60, 115])
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

    # Evidence frames for persons
    for p in persons:
        if p.get('evidence_frame_base64'):
            elements.extend(_embed_frame_image(p['evidence_frame_base64'],
                f'{p.get("person_id", "Person")} \u2014 Evidence', styles))
    return elements


def _build_weapons_pdf(weapons, styles):
    """Build weapons/objects detection table."""
    elements = []
    data = [['#', 'Object', 'Timestamp', 'Confidence', 'Held By', 'Evidence Ref']]
    for w in weapons:
        conf_level = w.get('confidence_level', 'medium').capitalize()
        conf_percent = w.get('confidence_percent', 75)
        data.append([
            str(w.get('index', '')),
            Paragraph(_safe_text(w.get('object', '')), styles['SmallText']),
            _safe_text(w.get('timestamp', 'N/A')),
            f'{conf_level} ({conf_percent}%)',
            _safe_text(w.get('held_by', 'N/A') if isinstance(w.get('held_by'), str) else 'N/A'),
            _safe_text(w.get('frame_ref', 'N/A')),
        ])
    if len(data) > 1:
        table = Table(data, colWidths=[20, 160, 65, 80, 75, 65])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#7f1d1d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, HexColor('#fef2f2')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(table)

    # Descriptions below
    for w in weapons:
        if w.get('description'):
            elements.append(Paragraph(
                f'<b>{_safe_text(w.get("object", ""))}:</b> {_safe_text(w["description"])}',
                styles['SmallText']
            ))
    return elements


def _build_legal_pdf(legal, styles):
    """Build legal classification section with IPC mapping and disclaimer."""
    elements = []

    # Disclaimer banner
    elements.append(Paragraph(
        '\u26a0 ' + _safe_text(legal.get('disclaimer', '')),
        styles['DisclaimerText']
    ))
    elements.append(Spacer(1, 4))

    # Classification table
    classifications = legal.get('classifications', [])
    if classifications:
        data = [['Activity Detected', 'Applicable Law', 'Description', 'Category']]
        for c in classifications:
            data.append([
                Paragraph(_safe_text(c.get('activity', ''))[:60], styles['SmallText']),
                _safe_text(c.get('applicable_law', '')),
                Paragraph(_safe_text(c.get('law_description', '')), styles['SmallText']),
                _safe_text(c.get('category', '').upper()),
            ])
        table = Table(data, colWidths=[140, 100, 150, 60])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), LEGAL_BORDER),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, LEGAL_BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LEGAL_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(table)
    return elements


def _build_confidence_matrix_pdf(matrix, styles):
    """Build AI confidence matrix table."""
    elements = []
    data = [['Detection Type', 'Confidence Level', 'System Estimate']]
    for detection_type, conf_data in matrix.items():
        label = conf_data.get('label', 'Unknown')
        percent = conf_data.get('percent', 75)
        
        level_color = GREEN if percent >= 85 else (AMBER if percent >= 70 else RED_ALERT)
        data.append([
            _safe_text(detection_type.replace('_', ' ').title()),
            Paragraph(f'<font color="{level_color.hexval()}">{label.upper()}</font>', styles['SmallText']),
            f'{percent}%',
        ])
    if len(data) > 1:
        table = Table(data, colWidths=[200, 80, 80])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
    return elements


def _build_chain_pdf(chain, styles):
    """Build chain of processing / evidence handling section."""
    elements = []
    statement = chain.get('statement', '')
    if statement:
        elements.append(Paragraph(_safe_text(statement), styles['BodyText']))
    steps = chain.get('processing_steps', [])
    if steps:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph('<b>Processing Steps:</b>', styles['SmallText']))
        for i, step in enumerate(steps):
            elements.append(Paragraph(f'{i + 1}. {_safe_text(step)}', styles['SmallText']))
    return elements


def _build_frame_index_pdf(frame_index, styles):
    """Build evidence frame index table."""
    elements = []
    data = [['Ref', 'Timestamp', 'Description', 'Findings']]
    for f in frame_index:
        findings_str = '; '.join(f.get('findings', []))[:80] or '\u2014'
        data.append([
            f.get('frame_ref', ''),
            f.get('timestamp', ''),
            _safe_text(f.get('description', ''))[:60] or '\u2014',
            Paragraph(_safe_text(findings_str), styles['SmallText']),
        ])
    if len(data) > 1:
        table = Table(data, colWidths=[35, 70, 180, 175])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), STEEL),
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


# ─────────────────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────────────────

def _safe_text(text):
    if not text:
        return ''
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def _section_divider():
    return HRFlowable(
        width="100%", thickness=0.5, color=HexColor('#e2e8f0'),
        spaceBefore=8, spaceAfter=4
    )


def _embed_frame_image(base64_str, caption, styles, max_width=3.5 * inch):
    elements = []
    img = _get_rl_image(base64_str, max_width)
    if img:
        elements.append(img)
        elements.append(Paragraph(_safe_text(caption), styles['CaptionText']))
        elements.append(Spacer(1, 6))
    return elements


def _get_rl_image(base64_str, max_width=3.5 * inch):
    if not base64_str:
        return None
    try:
        img_data = base64.b64decode(base64_str)
        img_buf = io.BytesIO(img_data)
        pil_img = PILImage.open(io.BytesIO(img_data))
        orig_w, orig_h = pil_img.size
        max_height = 3 * inch
        scale = min(max_width / orig_w, max_height / orig_h, 1.0)
        display_w = orig_w * scale
        display_h = orig_h * scale
        return RLImage(img_buf, width=display_w, height=display_h)
    except Exception as e:
        logger.warning(f"Could not embed image: {e}")
        return None


def _add_page_border(canvas_obj, doc):
    apply_page_watermarks(canvas_obj, doc, include_footer=True)
