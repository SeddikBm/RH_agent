"""
Génération PDF du rapport d'analyse — ReportLab uniquement.
Design professionnel : en-tête branded, sections colorées, pied de page avec numéro.
"""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.colors import HexColor
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate


# ── Palette ──────────────────────────────────────────────────
PRIMARY      = HexColor("#6366f1")
PRIMARY_DARK = HexColor("#4338ca")
PRIMARY_LIGHT= HexColor("#818cf8")
SUCCESS      = HexColor("#10b981")
SUCCESS_BG   = HexColor("#ecfdf5")
SUCCESS_BORDER = HexColor("#6ee7b7")
WARNING      = HexColor("#f59e0b")
WARNING_BG   = HexColor("#fffbeb")
WARNING_BORDER = HexColor("#fcd34d")
DANGER       = HexColor("#ef4444")
DANGER_BG    = HexColor("#fef2f2")
DANGER_BORDER= HexColor("#fca5a5")
DARK         = HexColor("#0f172a")
SLATE        = HexColor("#1e293b")
SLATE_2      = HexColor("#334155")
MUTED        = HexColor("#64748b")
LIGHT        = HexColor("#f8fafc")
BORDER       = HexColor("#e2e8f0")
WHITE        = colors.white
PAGE_W, PAGE_H = A4


def _rec_color(recommandation: str):
    r = recommandation.lower()
    if "recommandé" in r:
        return SUCCESS, SUCCESS_BG, SUCCESS_BORDER
    elif "considérer" in r:
        return WARNING, WARNING_BG, WARNING_BORDER
    return DANGER, DANGER_BG, DANGER_BORDER


def _score_color(score: float):
    if score >= 70:
        return SUCCESS
    elif score >= 50:
        return WARNING
    return DANGER


# ── Page callbacks (header + footer) ─────────────────────────

def _draw_page(canvas, doc, candidate: str, job: str, total_pages_ref: list):
    canvas.saveState()
    w, h = PAGE_W, PAGE_H

    # ── Top brand bar (indigo, full width) ──
    canvas.setFillColor(PRIMARY_DARK)
    canvas.rect(0, h - 12 * mm, w, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(20 * mm, h - 8 * mm, "AGENT RH  ·  Rapport d'Analyse de Candidature")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 20 * mm, h - 8 * mm,
                           datetime.now().strftime("%d/%m/%Y  %H:%M"))

    # ── Bottom footer bar ──
    canvas.setFillColor(LIGHT)
    canvas.rect(0, 0, w, 10 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 10 * mm, w - 20 * mm, 10 * mm)

    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(20 * mm, 3.5 * mm,
                      f"Candidat : {candidate}  ·  Poste : {job}")
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawRightString(w - 20 * mm, 3.5 * mm,
                           f"Page {doc.page}")

    canvas.restoreState()


def generate_analysis_pdf(analyse: dict, cv_name: str, job_title: str) -> bytes:
    """Génère le PDF du rapport d'analyse. Retourne les bytes du PDF."""
    rapport = analyse.get("rapport", {})
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=f"Rapport RH — {cv_name}",
        author="Agent RH IA",
        subject=f"Analyse de candidature — {job_title}",
    )

    # ── Styles ────────────────────────────────────────────────
    SS = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=SS["Normal"], **kw)

    H1 = sty("H1",
             fontSize=26, fontName="Helvetica-Bold",
             textColor=DARK, spaceAfter=2, leading=30)
    H2 = sty("H2",
             fontSize=10, fontName="Helvetica",
             textColor=MUTED, spaceAfter=10)
    SEC = sty("SEC",
              fontSize=13, fontName="Helvetica-Bold",
              textColor=SLATE, spaceBefore=14, spaceAfter=8,
              borderPad=0)
    BODY = sty("BODY",
               fontSize=10, fontName="Helvetica",
               textColor=SLATE_2, leading=16, spaceAfter=4,
               alignment=TA_JUSTIFY)
    BODY_SM = sty("BODY_SM",
                  fontSize=9, fontName="Helvetica",
                  textColor=MUTED, leading=14)
    BOLD = sty("BOLD",
               fontSize=10.5, fontName="Helvetica-Bold",
               textColor=DARK)
    CAPTION = sty("CAPTION",
                  fontSize=8, fontName="Helvetica",
                  textColor=MUTED, spaceAfter=2)

    scores = rapport.get("scores", {})
    score_global = scores.get("score_global", 0)
    recommandation = rapport.get("recommandation", "—")
    rec_color, rec_bg, rec_border = _rec_color(recommandation)

    story = []
    PW = doc.width  # usable page width

    # ══════════════════════════════════════════════════════════
    # SECTION 1 — En-tête candidat
    # ══════════════════════════════════════════════════════════

    story.append(Spacer(1, 4 * mm))

    # Candidate name + post
    story.append(Paragraph(cv_name, H1))
    story.append(Paragraph(
        f"Candidature au poste de <b>{job_title}</b>", H2))

    # Thin accent line
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY,
                             spaceAfter=10))

    # Info row: Score | Recommendation | Date
    score_c = _score_color(score_global)
    info_data = [[
        Paragraph(
            f"<font color='#64748b' size=8>SCORE GLOBAL</font><br/>"
            f"<font color='#{score_c.hexval()[2:]}' size=22><b>{score_global:.0f}</b></font>"
            f"<font color='#64748b' size=11> /100</font>",
            sty("SI", fontSize=10, fontName="Helvetica", leading=26)
        ),
        Paragraph(
            f"<font color='#64748b' size=8>RECOMMANDATION</font><br/>"
            f"<font color='#{rec_color.hexval()[2:]}' size=13><b>{recommandation}</b></font>",
            sty("RI", fontSize=10, fontName="Helvetica", leading=22)
        ),
        Paragraph(
            f"<font color='#64748b' size=8>MODÈLE IA</font><br/>"
            f"<font color='#334155' size=9>GPT-4o-mini · LangGraph</font><br/>"
            f"<font color='#64748b' size=8>BGE-small-en-v1.5</font>",
            sty("MI", fontSize=9, fontName="Helvetica", leading=16)
        ),
    ]]
    info_t = Table(info_data, colWidths=[PW * 0.25, PW * 0.45, PW * 0.30])
    info_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX",        (0, 0), (-1, -1), 1, BORDER),
        ("LINEAFTER",  (0, 0), (1, 0),   0.5, BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",    (0, 0), (-1, -1), 14),
    ]))
    story.append(info_t)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════
    # SECTION 2 — Scores par catégorie
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("SCORES PAR CATEGORIE", SEC))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

    score_items = [
        ("Compétences Techniques", scores.get("competences_techniques", 0), "40%"),
        ("Expérience professionnelle", scores.get("experience", 0), "30%"),
        ("Formation académique",       scores.get("formation", 0), "20%"),
        ("Soft Skills",                scores.get("soft_skills", 0), "10%"),
    ]

    BAR_W = PW - 6 * cm  # bar track max width (in points)
    for label, score, weight in score_items:
        sc = _score_color(score)
        pct = min(score / 100.0, 1.0)
        filled = BAR_W * pct
        empty = BAR_W - filled

        bar_data = [[
            Paragraph(f"{label} <font color='#94a3b8' size=8>({weight})</font>", BODY),
            # bar track: filled + empty side by side
            Table(
                [["", ""]],
                colWidths=[filled or 1, empty or 1],
                rowHeights=[8],
            ),
            Paragraph(
                f"<font color='#{sc.hexval()[2:]}' size=11><b>{score:.0f}</b></font>"
                f"<font color='#94a3b8' size=8>/100</font>",
                sty("SV", fontSize=10, fontName="Helvetica", alignment=TA_RIGHT)
            ),
        ]]
        # Style the mini bar
        bar_inner = bar_data[0][1]
        bar_inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), sc),
            ("BACKGROUND", (1, 0), (1, 0), BORDER),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING",    (0, 0), (-1, -1), 0),
        ]))

        row_t = Table(bar_data, colWidths=[5 * cm, BAR_W, 2 * cm])
        row_t.setStyle(TableStyle([
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING",    (0, 0), (-1, -1), 5),
            ("LINEBELOW",  (0, 0), (-1, -1), 0.3, HexColor("#f1f5f9")),
        ]))
        story.append(row_t)

    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════
    # SECTION 3 — Points forts / Lacunes (2 colonnes)
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("FORCES ET LACUNES", SEC))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

    pf_items = [Paragraph(f"<b>+</b>  {p}", BODY) for p in rapport.get("points_forts", [])]
    pl_items = [Paragraph(f"<b>-</b>  {p}", BODY) for p in rapport.get("points_faibles", [])]

    header_pf = Paragraph("[+] Points Forts", sty("PFH", fontSize=11, fontName="Helvetica-Bold",
                                                    textColor=SUCCESS, spaceAfter=8))
    header_pl = Paragraph("[!] Points a Ameliorer", sty("PLH", fontSize=11, fontName="Helvetica-Bold",
                                                          textColor=WARNING, spaceAfter=8))

    col_pf = [header_pf] + (pf_items or [Paragraph("—", BODY_SM)])
    col_pl = [header_pl] + (pl_items or [Paragraph("—", BODY_SM)])

    two_col = Table([[col_pf, col_pl]], colWidths=[PW / 2 - 3 * mm, PW / 2 - 3 * mm])
    two_col.setStyle(TableStyle([
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("PADDING",    (0, 0), (-1, -1), 12),
        ("BACKGROUND", (0, 0), (0, -1), SUCCESS_BG),
        ("BACKGROUND", (1, 0), (1, -1), WARNING_BG),
        ("BOX",        (0, 0), (0, -1), 1, SUCCESS_BORDER),
        ("BOX",        (1, 0), (1, -1), 1, WARNING_BORDER),
        ("LINEAFTER",  (0, 0), (0, -1), 0, WHITE),  # gap between cols
    ]))
    story.append(two_col)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════
    # SECTION 4 — Adéquation au poste
    # ══════════════════════════════════════════════════════════
    adequation = rapport.get("adequation_poste", "")
    if adequation:
        story.append(Paragraph("ADEQUATION AU POSTE", SEC))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

        adeq_t = Table([[Paragraph(adequation, BODY)]], colWidths=[PW])
        adeq_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("BOX",        (0, 0), (-1, -1), 1, BORDER),
            ("PADDING",    (0, 0), (-1, -1), 14),
            ("LEFTPADDING",(0, 0), (-1, -1), 16),
        ]))
        story.append(adeq_t)
        story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════
    # SECTION 5 — Justification recommandation
    # ══════════════════════════════════════════════════════════
    justif = rapport.get("justification_recommandation", "")
    if justif:
        story.append(Paragraph("JUSTIFICATION DE LA RECOMMANDATION", SEC))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

        justif_t = Table([[Paragraph(justif, BODY)]], colWidths=[PW])
        justif_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), rec_bg),
            ("BOX",        (0, 0), (-1, -1), 1.5, rec_border),
            ("PADDING",    (0, 0), (-1, -1), 14),
            ("LEFTPADDING",(0, 0), (-1, -1), 16),
        ]))
        story.append(justif_t)
        story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════
    # SECTION 6 — Correspondances des compétences
    # ══════════════════════════════════════════════════════════
    correspondances = rapport.get("correspondances_competences", [])
    if correspondances:
        story.append(Paragraph("CORRESPONDANCES DES COMPETENCES", SEC))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

        niveau_cfg = {
            "excellent": (SUCCESS,          HexColor("#dcfce7"), "EXCELLENT"),
            "bon":       (HexColor("#3b82f6"), HexColor("#dbeafe"), "BON"),
            "partiel":   (WARNING,           HexColor("#fef9c3"), "PARTIEL"),
            "faible":    (HexColor("#f97316"), HexColor("#ffedd5"), "FAIBLE"),
            "absent":    (DANGER,            DANGER_BG,            "ABSENT"),
        }

        # Table header
        hdr = Table(
            [[
                Paragraph("COMPÉTENCE", sty("CH", fontSize=8, fontName="Helvetica-Bold",
                                             textColor=MUTED)),
                Paragraph("NIVEAU", sty("CH2", fontSize=8, fontName="Helvetica-Bold",
                                         textColor=MUTED, alignment=TA_CENTER)),
                Paragraph("JUSTIFICATION", sty("CH3", fontSize=8, fontName="Helvetica-Bold",
                                                textColor=MUTED)),
            ]],
            colWidths=[5 * cm, 2.5 * cm, PW - 7.5 * cm],
        )
        hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("PADDING",    (0, 0), (-1, -1), 7),
            ("LINEBELOW",  (0, 0), (-1, -1), 1, BORDER),
        ]))
        story.append(hdr)

        for i, comp in enumerate(correspondances[:14]):
            niveau = comp.get("niveau_match", "absent")
            nc, nbg, nlabel = niveau_cfg.get(niveau, niveau_cfg["absent"])
            row_bg = HexColor("#f8fafc") if i % 2 == 0 else WHITE

            comp_row = Table(
                [[
                    Paragraph(comp.get("competence_requise", ""), BOLD),
                    Paragraph(
                        f"<font color='#{nc.hexval()[2:]}' size=8><b> {nlabel} </b></font>",
                        sty("NL", fontSize=8, fontName="Helvetica-Bold", alignment=TA_CENTER)
                    ),
                    Paragraph(comp.get("justification", ""), BODY_SM),
                ]],
                colWidths=[5 * cm, 2.5 * cm, PW - 7.5 * cm],
            )
            comp_row.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), row_bg),
                ("BACKGROUND", (1, 0), (1, 0),   nbg),
                ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                ("PADDING",    (0, 0), (-1, -1), 7),
                ("LINEBELOW",  (0, 0), (-1, -1), 0.3, BORDER),
            ]))
            story.append(comp_row)

        story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════
    # SECTION 7 — Disclaimer éthique
    # ══════════════════════════════════════════════════════════
    disclaimer_text = rapport.get("disclaimer", "")
    non_sub = rapport.get("non_substitution", "")

    if disclaimer_text or non_sub:
        story.append(Spacer(1, 3 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))

        disclaimer_style = sty("DISC", fontSize=8.5, fontName="Helvetica",
                                textColor=HexColor("#78716c"), leading=14,
                                alignment=TA_JUSTIFY)

        # Clean emoji characters that ReportLab can't render
        clean_disclaimer = disclaimer_text.replace("⚠️", "").replace("🤝", "").strip()
        clean_nonsub = non_sub.replace("⚠️", "").replace("🤝", "").strip()

        disc_rows = []
        if clean_disclaimer:
            disc_rows.append([Paragraph(
                f"<b>AVERTISSEMENT :</b> {clean_disclaimer}", disclaimer_style
            )])
        if clean_nonsub:
            disc_rows.append([Paragraph(
                f"<b>NON-SUBSTITUTION :</b> {clean_nonsub}", disclaimer_style
            )])

        if disc_rows:
            disc_t = Table(disc_rows, colWidths=[PW])
            disc_t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fefce8")),
                ("BOX",        (0, 0), (-1, -1), 1, HexColor("#fde68a")),
                ("PADDING",    (0, 0), (-1, -1), 12),
            ]))
            story.append(disc_t)

    # ── Build with page callback ──────────────────────────────
    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_page(c, d, cv_name, job_title, []),
        onLaterPages=lambda c, d: _draw_page(c, d, cv_name, job_title, []),
    )
    return buffer.getvalue()
