"""
Nœud 4 — Génération du rapport final structuré.
Synthétise toutes les informations en un rapport complet.
"""
from loguru import logger
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured

DISCLAIMER_RH = (
    "⚠️ AVERTISSEMENT IMPORTANT : Ce rapport est un outil d'aide à la décision "
    "généré automatiquement par un système d'intelligence artificielle. "
    "Il ne constitue pas une évaluation définitive du candidat et ne remplace "
    "en aucun cas le jugement professionnel d'un recruteur ou d'un expert RH qualifié. "
    "Les informations fournies doivent être vérifiées et validées par l'équipe "
    "de recrutement avant toute décision. La décision finale appartient exclusivement "
    "aux professionnels humains responsables du recrutement."
)


# ── Schéma Pydantic ───────────────────────────────────────

class RapportFinal(BaseModel):
    points_forts: list[str] = Field(default_factory=list, description="3-5 points forts du candidat")
    points_faibles: list[str] = Field(default_factory=list, description="3-5 points d'amélioration")
    adequation_poste: str = Field(..., description="Synthèse de l'adéquation (3-4 phrases)")
    recommandation: str = Field(..., description="Une des options: 'Entretien recommandé', 'À considérer', 'Profil insuffisant'")
    justification_recommandation: str = Field(..., description="Justification de la recommandation (2-3 phrases)")

    class Config:
        extra = "ignore"


# ── Prompt ────────────────────────────────────────────────

RAPPORT_PROMPT = """
Tu es un expert RH. Génère un rapport de candidature professionnel et objectif.

POSTE : {job_titre} chez {entreprise}
CANDIDAT : {nom_candidat}

SCORES OBTENUS :
- Compétences techniques : {score_ct}/100 → {just_ct}
- Expérience : {score_exp}/100 → {just_exp}
- Formation : {score_form}/100 → {just_form}
- Soft skills : {score_ss}/100 → {just_ss}
- Score global pondéré : {score_global}/100

POINTS CLÉS DU MATCHING :
{matching_summary}

Génère :
1. 3 à 5 points forts CONCRETS du candidat pour ce poste
2. 3 à 5 points faibles ou lacunes importantes
3. Une synthèse de l'adéquation au poste (3-4 phrases professionnelles)
4. Une recommandation parmi : "Entretien recommandé", "À considérer", "Profil insuffisant"
   - "Entretien recommandé" : score global ≥ 70
   - "À considérer" : score global entre 50 et 69
   - "Profil insuffisant" : score global < 50
5. La justification de cette recommandation (2-3 phrases)

Sois objectif, factuel et bienveillant. Évite tout jugement personnel.
Réponds en JSON conforme au schéma.
"""


def _get_recommendation_from_score(score: float) -> str:
    """Détermine la recommandation basée sur le score global."""
    if score >= 70:
        return "Entretien recommandé"
    elif score >= 50:
        return "À considérer"
    else:
        return "Profil insuffisant"


# ── Nœud LangGraph ────────────────────────────────────────

async def report_node(state: AnalysisState) -> dict:
    """
    Étape 4 du pipeline : Génération du rapport final.
    Produit le rapport complet avec disclaimer.
    """
    logger.info(f"📝 [Nœud 4] Génération du rapport | CV: {state['cv_id']}")

    job = state["job_description"]
    scores = state.get("scores") or {}
    skill_matches = state.get("skill_matches", [])
    cv_struct = state.get("cv_structure") or {}

    # Préparer le résumé du matching
    matching_lines = []
    for m in skill_matches[:8]:
        niveau = m.get("niveau_match", "?")
        comp = m.get("competence_requise", "?")
        just = m.get("justification", "")
        matching_lines.append(f"• {comp}: [{niveau.upper()}] — {just}")
    matching_summary = "\n".join(matching_lines) or "Non disponible"

    justifications = scores.get("justifications", {})

    try:
        result = await invoke_structured(
            prompt_template=RAPPORT_PROMPT,
            variables={
                "job_titre": job.get("titre", "Non précisé"),
                "entreprise": job.get("entreprise", "Non précisée"),
                "nom_candidat": cv_struct.get("nom_complet", "Candidat anonyme"),
                "score_ct": scores.get("competences_techniques", 0),
                "just_ct": justifications.get("competences_techniques", ""),
                "score_exp": scores.get("experience", 0),
                "just_exp": justifications.get("experience", ""),
                "score_form": scores.get("formation", 0),
                "just_form": justifications.get("formation", ""),
                "score_ss": scores.get("soft_skills", 0),
                "just_ss": justifications.get("soft_skills", ""),
                "score_global": scores.get("score_global", 0),
                "matching_summary": matching_summary,
            },
            output_schema=RapportFinal,
            temperature=0.2,
        )

        rapport = {
            "scores": {
                "competences_techniques": scores.get("competences_techniques", 0),
                "experience": scores.get("experience", 0),
                "formation": scores.get("formation", 0),
                "soft_skills": scores.get("soft_skills", 0),
                "score_global": scores.get("score_global", 0),
            },
            "points_forts": result.points_forts,
            "points_faibles": result.points_faibles,
            "correspondances_competences": skill_matches,
            "adequation_poste": result.adequation_poste,
            "recommandation": result.recommandation,
            "justification_recommandation": result.justification_recommandation,
            "disclaimer": DISCLAIMER_RH,
            # Méta-données pour la traçabilité
            "nom_candidat": cv_struct.get("nom_complet"),
            "titre_poste": job.get("titre"),
            "entreprise": job.get("entreprise"),
        }

        logger.info(
            f"✅ Rapport généré | Score: {scores.get('score_global', 0):.1f} "
            f"| Recommandation: {result.recommandation}"
        )

        return {"rapport": rapport, "guardrail_valide": False}  # Sera validé par le nœud garde-fou

    except Exception as e:
        logger.error(f"❌ [Nœud 4] Erreur génération rapport: {e}")
        # Rapport de fallback minimal
        score_global = scores.get("score_global", 0)
        fallback_rapport = {
            "scores": scores,
            "points_forts": ["Analyse partielle disponible"],
            "points_faibles": ["Rapport incomplet en raison d'une erreur technique"],
            "correspondances_competences": skill_matches,
            "adequation_poste": "Rapport généré partiellement suite à une erreur technique.",
            "recommandation": _get_recommendation_from_score(score_global),
            "justification_recommandation": f"Score global calculé: {score_global:.1f}/100",
            "disclaimer": DISCLAIMER_RH,
        }
        return {"rapport": fallback_rapport, "guardrail_valide": False, "erreur": str(e)}
