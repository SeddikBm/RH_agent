import io
from weasyprint import HTML

def generate_analysis_pdf(analyse: dict, cv_name: str, job_title: str) -> bytes:
    """Génère un PDF stylisé avec les résultats de l'analyse via WeasyPrint."""
    
    rapport = analyse.get("rapport", {})
    scores = rapport.get("scores", {})
    points_forts = rapport.get("points_forts", [])
    points_faibles = rapport.get("points_faibles", [])
    correspondances = rapport.get("correspondances_competences", [])

    pf_html = "".join([f"<li>{pf}</li>" for pf in points_forts])
    pf_faibles_html = "".join([f"<li>{pf}</li>" for pf in points_faibles])
    
    # Couleurs et labels pour les niveaux de match
    MATCH_STYLES = {
        "excellent": ("background:#d4edda; color:#155724; border:1px solid #c3e6cb;", "✔ Excellent"),
        "bon":       ("background:#cce5ff; color:#004085; border:1px solid #b8daff;", "✔ Bon"),
        "partiel":   ("background:#fff3cd; color:#856404; border:1px solid #ffeeba;", "~ Partiel"),
        "faible":    ("background:#f8d7da; color:#721c24; border:1px solid #f5c6cb;", "✖ Faible"),
        "absent":    ("background:#e2e3e5; color:#383d41; border:1px solid #d6d8db;", "✖ Absent"),
    }

    table_rows = []
    for c in correspondances:
        req = c.get("competence_requise", "")
        lvl = c.get("niveau_match", "").lower()
        just = c.get("justification", "")
        style, label = MATCH_STYLES.get(lvl, ("background:#e2e3e5; color:#383d41;", lvl.capitalize()))
        badge = f'<span style="{style} padding:2px 8px; border-radius:4px; font-size:10px; font-weight:bold; white-space:nowrap;">{label}</span>'
        row_html = f"""
        <tr>
            <td class="align-left" style="min-width:120px; max-width:200px; word-break:break-word;">{req}</td>
            <td class="align-center" style="min-width:100px;">{badge}</td>
            <td class="align-left observations" style="min-width:180px; word-break:break-word;">{just}</td>
        </tr>
        """
        table_rows.append(row_html)
    table_body = "".join(table_rows)

    adq = rapport.get("adequation_poste", "Pas d'analyse détaillée disponible.")
    rec = rapport.get("recommandation", "N/A")
    just_rec = rapport.get("justification_recommandation", "")
    score = scores.get("score_global", 0)

    # Couleur de la score box selon le score
    if score >= 70:
        score_border = "#28a745"
        score_bg = "#f0fff4"
        score_color = "#155724"
    elif score >= 50:
        score_border = "#fd7e14"
        score_bg = "#fff8f0"
        score_color = "#7d4000"
    else:
        score_border = "#dc3545"
        score_bg = "#fff5f5"
        score_color = "#721c24"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Rapport d'Analyse: {cv_name}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
            
            body {{
                font-family: 'Roboto', 'Helvetica', 'Arial', sans-serif;
                color: #2d3748;
                font-size: 11px;
                line-height: 1.6;
                padding: 36px 44px;
                background-color: #ffffff;
            }}
            
            /* ── En-tête ── */
            .report-header {{
                text-align: center;
                margin-bottom: 24px;
                padding-bottom: 16px;
                border-bottom: 3px solid #2b4a8b;
            }}
            
            h1 {{
                color: #1A365D;
                font-size: 22px;
                font-weight: bold;
                margin-bottom: 4px;
            }}
            
            .header-subtitle {{
                font-size: 12px;
                color: #4A5568;
                margin-top: 2px;
            }}
            
            h2 {{
                color: #1A365D;
                font-size: 14px;
                font-weight: bold;
                margin-top: 24px;
                margin-bottom: 8px;
                padding: 6px 10px;
                background-color: #EBF4FF;
                border-left: 4px solid #2b4a8b;
                border-radius: 0 4px 4px 0;
            }}
            
            /* ── Infos candidat ── */
            .meta-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 16px;
                font-size: 11px;
            }}
            .meta-table td {{
                padding: 5px 10px;
                border: 1px solid #CBD5E0;
            }}
            .meta-table td:first-child {{
                font-weight: bold;
                background-color: #EDF2F7;
                color: #2D3748;
                width: 140px;
            }}
            
            /* ── Score box ── */
            .score-box {{
                background-color: {score_bg};
                border: 2px solid {score_border};
                padding: 14px 20px;
                border-radius: 8px;
                text-align: center;
                font-size: 22px;
                font-weight: bold;
                color: {score_color};
                margin: 16px auto;
                width: 50%;
            }}
            .score-box .score-label {{
                font-size: 11px;
                color: #4A5568;
                font-weight: normal;
                display: block;
                margin-top: 2px;
            }}
            
            /* ── Recommandation ── */
            .recommendation-box {{
                padding: 10px 14px;
                border-radius: 6px;
                margin-top: 8px;
                font-size: 12px;
            }}
            
            /* ── Grid points forts/faibles ── */
            .grid {{
                display: flex;
                gap: 16px;
                margin-top: 8px;
            }}
            .col {{
                flex: 1;
                padding: 12px;
                border-radius: 6px;
            }}
            .col-forts {{
                background-color: #f0fff4;
                border: 1px solid #c6f6d5;
                border-left: 4px solid #38a169;
            }}
            .col-faibles {{
                background-color: #fff5f5;
                border: 1px solid #fed7d7;
                border-left: 4px solid #e53e3e;
            }}
            .col h2 {{
                margin-top: 0;
                margin-bottom: 8px;
                font-size: 12px;
                background: none;
                border-left: none;
                padding: 0;
                color: #2D3748;
            }}
            ul {{ padding-left: 14px; margin: 0; }}
            li {{ margin-bottom: 5px; }}
            
            /* ── Tableau compétences ── */
            .competence-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 10.5px;
                table-layout: fixed;
            }}
            .competence-table th, .competence-table td {{
                border: 1px solid #CBD5E0;
                padding: 8px 10px;
                vertical-align: top;
            }}
            .competence-table th {{
                background-color: #1A365D;
                color: white;
                font-weight: bold;
                text-align: center;
                font-size: 11px;
                letter-spacing: 0.03em;
            }}
            .competence-table th:nth-child(1) {{ width: 27%; }}
            .competence-table th:nth-child(2) {{ width: 18%; }}
            .competence-table th:nth-child(3) {{ width: 55%; }}
            .competence-table tr:nth-child(even) {{ background-color: #F7FAFC; }}
            .competence-table tr:hover {{ background-color: #EBF8FF; }}
            
            .align-left {{ text-align: left; }}
            .align-center {{ text-align: center; vertical-align: middle; }}
            .observations {{ color: #4A5568; }}
            
            /* ── Conclusion ── */
            .conclusion-text {{
                font-size: 11px;
                line-height: 1.7;
                color: #2D3748;
                padding: 10px 14px;
                background: #F7FAFC;
                border-left: 4px solid #2b4a8b;
                border-radius: 0 4px 4px 0;
            }}
            
            /* ── Footer ── */
            .disclaimer {{
                margin-top: 40px;
                font-size: 9px;
                color: #4A5568;
                font-style: italic;
                text-align: center;
                border-top: 2px solid #CBD5E0;
                padding-top: 12px;
                background-color: #EDF2F7;
                padding: 12px 16px;
                border-radius: 0 0 4px 4px;
            }}
            .disclaimer strong {{
                color: #2D3748;
                font-style: normal;
            }}
        </style>
    </head>
    <body>
        <div class="report-header">
            <h1>Rapport d'Évaluation de Candidature</h1>
            <div class="header-subtitle">Généré automatiquement par le Système Agent RH IA</div>
        </div>

        <table class="meta-table">
            <tr><td>Candidat</td><td>{cv_name}</td></tr>
            <tr><td>Poste ciblé</td><td>{job_title}</td></tr>
        </table>

        <div class="score-box">
            {score}%
            <span class="score-label">Score Global d'Adéquation</span>
        </div>
        
        <h2>Recommandation Globale</h2>
        <p><strong>Décision IA :</strong> {rec}</p>
        <p><em>{just_rec}</em></p>

        <h2>Points Forts & Axes d'Amélioration</h2>
        <div class="grid">
            <div class="col col-forts">
                <h2>✅ Points Forts</h2>
                <ul>{pf_html}</ul>
            </div>
            <div class="col col-faibles">
                <h2>⚠️ Axes d'Amélioration</h2>
                <ul>{pf_faibles_html}</ul>
            </div>
        </div>

        <h2>Analyse Détaillée des Compétences</h2>
        <table class="competence-table">
            <thead>
                <tr>
                    <th>Compétence Requise</th>
                    <th>Niveau Match</th>
                    <th>Observations</th>
                </tr>
            </thead>
            <tbody>
                {table_body}
            </tbody>
        </table>
        
        <h2>Conclusion</h2>
        <div class="conclusion-text">{adq}</div>

        <div class="disclaimer">
            <strong>⚠️ AVERTISSEMENT IMPORTANT</strong> — Ce rapport a été généré automatiquement par une Intelligence Artificielle.
            Il sert uniquement d'aide à la décision et ne remplace pas le jugement professionnel d'un recruteur qualifié.
            La décision finale appartient exclusivement aux professionnels humains responsables du recrutement.
        </div>
    </body>
    </html>
    """
    
    # Génération du PDF avec weasyprint
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes
