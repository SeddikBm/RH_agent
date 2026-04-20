"""
Génération PDF du rapport d'analyse — ReportLab uniquement (léger, sans dépendances système).
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.colors import HexColor


# ── Palette de couleurs ────────────────────────────────────────
PRIMARY = HexColor("#6366f1")
PRIMARY_DARK = HexColor("#4f46e5")
SUCCESS = HexColor("#10b981")
WARNING = HexColor("#f59e0b")
DANGER = HexColor("#ef4444")
DARK = HexColor("#0f172a")
DARK2 = HexColor("#1e293b")
MUTED = HexColor("#64748b")
LIGHT = HexColor("#f1f5f9")
WHITE = colors.white


def _rec_color(recommandation: str):
    if "recommandé" in recommandation.lower():
        return SUCCESS
    elif "considérer" in recommandation.lower():
        return WARNING
    return DANGER


def _score_color(score: float):
    if score >= 70:
        return SUCCESS
    elif score >= 50:
        return WARNING
    return DANGER


def generate_analysis_pdf(analyse: dict, cv_name: str, job_title: str) -> bytes:
    """Génère le PDF du rapport d'analyse. Retourne les bytes du PDF."""
    rapport = analyse.get("rapport", {})
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=f"Rapport RH — {cv_name}",
        author="Agent RH IA",
    )

    styles = getSampleStyleSheet()
    story = []

    # ── Styles personnalisés ──────────────────────────────────
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Normal"],
        fontSize=24, fontName="Helvetica-Bold",
        textColor=HexColor("#111827"), alignment=TA_LEFT,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Normal"],
        fontSize=10, fontName="Helvetica",
        textColor=HexColor("#6b7280"), alignment=TA_RIGHT,
    )
    section_title_style = ParagraphStyle(
        "SectionTitle", parent=styles["Normal"],
        fontSize=14, fontName="Helvetica-Bold",
        textColor=HexColor("#1f2937"), spaceBefore=18, spaceAfter=10,
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10.5, fontName="Helvetica",
        textColor=HexColor("#374151"), leading=16, spaceAfter=6,
    )
    muted_style = ParagraphStyle(
        "Muted", parent=styles["Normal"],
        fontSize=9.5, fontName="Helvetica",
        textColor=HexColor("#9ca3af"), leading=14,
    )
    bold_style = ParagraphStyle(
        "Bold", parent=styles["Normal"],
        fontSize=10.5, fontName="Helvetica-Bold",
        textColor=HexColor("#111827"),
    )

    # ══════════════════════════════════════════════════════════
    # EN-TÊTE
    # ══════════════════════════════════════════════════════════
    header_data = [[
        Paragraph(f"Rapport d'Analyse RH", title_style),
        Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y')}<br/>à {datetime.now().strftime('%H:%M')}", subtitle_style),
    ]]
    header_table = Table(header_data, colWidths=[11 * cm, 6 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 2, PRIMARY),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.6 * cm))

    # Info candidat + poste
    scores = rapport.get("scores", {})
    score_global = scores.get("score_global", 0)
    recommandation = rapport.get("recommandation", "—")
    rec_color = _rec_color(recommandation)

    info_data = [
        [
            Paragraph(f"<font color='#6b7280'>Candidat</font><br/><b>{cv_name}</b>", body_style),
            Paragraph(f"<font color='#6b7280'>Poste Ciblé</font><br/><b>{job_title}</b>", body_style),
            Paragraph(f"<font color='#6b7280'>Score Global</font><br/><font color='#{rec_color.hexval()[2:]}' size=14><b>{score_global:.0f}/100</b></font>", body_style),
        ]
    ]
    info_table = Table(info_data, colWidths=[5 * cm, 7 * cm, 5 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
        ("PADDING", (0, 0), (-1, -1), 14),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1, HexColor("#e5e7eb")),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5 * cm))

    # Recommandation badge
    rec_data = [[Paragraph(f"<b>RECOMMANDATION : {recommandation.upper()}</b>", ParagraphStyle(
        "Rec", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_CENTER,
    ))]]
    rec_table = Table(rec_data, colWidths=[17 * cm])
    rec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rec_color),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 0.5 * cm))

    # ══════════════════════════════════════════════════════════
    # SCORES PAR CATÉGORIE
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("Scores par Catégorie", section_title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.2 * cm))

    score_items = [
        ("Compétences Techniques (40%)", scores.get("competences_techniques", 0)),
        ("Expérience (30%)", scores.get("experience", 0)),
        ("Formation (20%)", scores.get("formation", 0)),
        ("Soft Skills (10%)", scores.get("soft_skills", 0)),
    ]

    for label, score in score_items:
        sc = _score_color(score)
        row = [
            Paragraph(label, body_style),
            Paragraph(f"<b>{score:.0f}/100</b>", ParagraphStyle(
                "S", parent=styles["Normal"],
                fontSize=11, fontName="Helvetica-Bold",
                textColor=sc, alignment=TA_RIGHT,
            )),
        ]
        t = Table([row], colWidths=[14 * cm, 3 * cm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#f1f5f9")),
        ]))
        story.append(t)

    story.append(Spacer(1, 0.5 * cm))

    # ══════════════════════════════════════════════════════════
    # POINTS FORTS / LACUNES
    # ══════════════════════════════════════════════════════════
    pf_data = [
        [
            [Paragraph("✅ Points Forts", ParagraphStyle("PFT", parent=styles["Normal"],
                fontSize=12, fontName="Helvetica-Bold", textColor=SUCCESS, spaceAfter=6))],
            [Paragraph("⚠️ Points à Améliorer", ParagraphStyle("PLT", parent=styles["Normal"],
                fontSize=12, fontName="Helvetica-Bold", textColor=WARNING, spaceAfter=6))],
        ]
    ]

    pf_content = [Paragraph(f"• {p}", body_style) for p in rapport.get("points_forts", [])]
    pl_content = [Paragraph(f"• {p}", body_style) for p in rapport.get("points_faibles", [])]

    pf_table_data = [[pf_content or [Paragraph("—", muted_style)],
                      pl_content or [Paragraph("—", muted_style)]]]
    pf_table = Table(pf_table_data, colWidths=[8.5 * cm, 8.5 * cm])
    pf_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (0, -1), HexColor("#f0fdf4")),
        ("BACKGROUND", (1, 0), (1, -1), HexColor("#fffbeb")),
        ("BOX", (0, 0), (0, -1), 1, HexColor("#bbf7d0")),
        ("BOX", (1, 0), (1, -1), 1, HexColor("#fde68a")),
    ]))
    story.append(Paragraph("Forces & Lacunes", section_title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    story.append(Spacer(1, 0.2 * cm))
    story.append(pf_table)
    story.append(Spacer(1, 0.5 * cm))

    # ══════════════════════════════════════════════════════════
    # ADÉQUATION AU POSTE
    # ══════════════════════════════════════════════════════════
    adequation = rapport.get("adequation_poste", "")
    if adequation:
        story.append(Paragraph("Adéquation au Poste", section_title_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
        story.append(Spacer(1, 0.2 * cm))
        adeq_table = Table([[Paragraph(adequation, body_style)]], colWidths=[17 * cm])
        adeq_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f8fafc")),
            ("PADDING", (0, 0), (-1, -1), 12),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#e2e8f0")),
        ]))
        story.append(adeq_table)
        story.append(Spacer(1, 0.5 * cm))

    # ══════════════════════════════════════════════════════════
    # CORRESPONDANCES DES COMPÉTENCES
    # ══════════════════════════════════════════════════════════
    correspondances = rapport.get("correspondances_competences", [])
    if correspondances:
        story.append(Paragraph("Correspondances des Compétences", section_title_style))
        story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
        story.append(Spacer(1, 0.2 * cm))

        niveau_colors = {
            "excellent": SUCCESS,
            "bon": HexColor("#3b82f6"),
            "partiel": WARNING,
            "faible": HexColor("#f97316"),
            "absent": DANGER,
        }

        for comp in correspondances[:12]:
            niveau = comp.get("niveau_match", "absent")
            nc = niveau_colors.get(niveau, MUTED)
            comp_data = [[
                Paragraph(comp.get("competence_requise", ""), bold_style),
                Paragraph(f"<b>{niveau.upper()}</b>", ParagraphStyle(
                    "NM", parent=styles["Normal"],
                    fontSize=9, fontName="Helvetica-Bold",
                    textColor=nc, alignment=TA_CENTER,
                )),
                Paragraph(comp.get("justification", ""), muted_style),
            ]]
            ct = Table(comp_data, colWidths=[5 * cm, 2.5 * cm, 9.5 * cm])
            ct.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#f1f5f9")),
                ("BACKGROUND", (1, 0), (1, 0), HexColor(f"{nc.hexval()[:-2]}22")),
            ]))
            story.append(ct)

        story.append(Spacer(1, 0.5 * cm))

    # ══════════════════════════════════════════════════════════
    # DISCLAIMER
    # ══════════════════════════════════════════════════════════
    disclaimer_text = rapport.get("disclaimer", "")
    non_sub = rapport.get("non_substitution", "")

    disclaimer_content = []
    if disclaimer_text:
        disclaimer_content.append(Paragraph(disclaimer_text, muted_style))
    if non_sub:
        disclaimer_content.append(Spacer(1, 0.2 * cm))
        disclaimer_content.append(Paragraph(non_sub, muted_style))

    if disclaimer_content:
        dt = Table([disclaimer_content], colWidths=[17 * cm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fef3c7")),
            ("PADDING", (0, 0), (-1, -1), 12),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#fde68a")),
        ]))
        story.append(dt)

    doc.build(story)
    return buffer.getvalue()
