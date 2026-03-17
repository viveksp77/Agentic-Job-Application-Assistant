import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from typing import Optional


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
DARK_BG    = colors.HexColor('#0d0f14')
ACCENT     = colors.HexColor('#6366f1')
TEXT_DARK  = colors.HexColor('#1a1a2e')
TEXT_MUTED = colors.HexColor('#6b7280')
WHITE      = colors.white


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'title',
            parent=base['Normal'],
            fontSize=20,
            fontName='Helvetica-Bold',
            textColor=TEXT_DARK,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        'subtitle': ParagraphStyle(
            'subtitle',
            parent=base['Normal'],
            fontSize=11,
            fontName='Helvetica',
            textColor=TEXT_MUTED,
            spaceAfter=16,
            alignment=TA_LEFT,
        ),
        'section_header': ParagraphStyle(
            'section_header',
            parent=base['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            textColor=ACCENT,
            spaceBefore=14,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        'body': ParagraphStyle(
            'body',
            parent=base['Normal'],
            fontSize=10,
            fontName='Helvetica',
            textColor=TEXT_DARK,
            spaceAfter=6,
            leading=16,
            alignment=TA_JUSTIFY,
        ),
        'bullet': ParagraphStyle(
            'bullet',
            parent=base['Normal'],
            fontSize=10,
            fontName='Helvetica',
            textColor=TEXT_DARK,
            spaceAfter=5,
            leading=15,
            leftIndent=12,
            bulletIndent=0,
            alignment=TA_LEFT,
        ),
    }


def _divider():
    return HRFlowable(
        width='100%',
        thickness=0.5,
        color=colors.HexColor('#e5e7eb'),
        spaceAfter=10,
        spaceBefore=4,
    )


# ---------------------------------------------------------------------------
# Cover letter PDF
# ---------------------------------------------------------------------------

def generate_cover_letter_pdf(
    cover_letter_text: str,
    job_title: str = 'the role',
    candidate_name: str = '',
) -> bytes:
    """
    Generate a professionally formatted cover letter PDF.

    Args:
        cover_letter_text: Full cover letter text.
        job_title:         Job title for the header.
        candidate_name:    Optional candidate name for the header.

    Returns:
        PDF as bytes — ready to send as a file download.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    s = _styles()
    story = []

    # Header
    name_line = candidate_name if candidate_name else 'Cover Letter'
    story.append(Paragraph(name_line, s['title']))
    story.append(Paragraph(f'Application for: {job_title}', s['subtitle']))
    story.append(_divider())

    # Body — split into paragraphs
    paragraphs = [p.strip() for p in cover_letter_text.strip().split('\n\n') if p.strip()]
    for para in paragraphs:
        # Replace single newlines with spaces within a paragraph
        para_clean = para.replace('\n', ' ')
        story.append(Paragraph(para_clean, s['body']))
        story.append(Spacer(1, 6))

    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Resume bullets PDF
# ---------------------------------------------------------------------------

def generate_resume_pdf(
    bullets_text: str,
    job_title: str = 'the role',
    candidate_name: str = '',
    resume_skills: list = None,
    missing_skills: list = None,
) -> bytes:
    """
    Generate a formatted resume optimisation PDF with bullets and skill summary.

    Args:
        bullets_text:   Optimised resume bullet points (• or - prefixed lines).
        job_title:      Target job title.
        candidate_name: Optional candidate name.
        resume_skills:  List of matched skills.
        missing_skills: List of skills to develop.

    Returns:
        PDF as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    s = _styles()
    story = []

    # Header
    name_line = candidate_name if candidate_name else 'Optimised Resume'
    story.append(Paragraph(name_line, s['title']))
    story.append(Paragraph(f'Tailored for: {job_title}', s['subtitle']))
    story.append(_divider())

    # Optimised bullets section
    story.append(Paragraph('Optimised Experience Bullets', s['section_header']))

    lines = [l.strip() for l in bullets_text.strip().split('\n') if l.strip()]
    for line in lines:
        # Strip bullet characters and re-add as proper bullet
        clean = line.lstrip('•-*– ').strip()
        if clean:
            story.append(Paragraph(f'• {clean}', s['bullet']))

    # Skills summary section
    if resume_skills:
        story.append(Spacer(1, 10))
        story.append(_divider())
        story.append(Paragraph('Matched Skills', s['section_header']))
        skills_text = '  •  '.join(resume_skills[:12])
        story.append(Paragraph(skills_text, s['body']))

    if missing_skills:
        story.append(Spacer(1, 6))
        story.append(Paragraph('Skills to Develop', s['section_header']))
        missing_text = '  •  '.join(missing_skills[:8])
        story.append(Paragraph(missing_text, s['body']))

    doc.build(story)
    return buffer.getvalue()