"""
Nœud 4 — Génération du rapport final structuré.
Synthétise toutes les informations avec garde-fous éthiques.
"""
from loguru import logger
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured

DISCLAIMER = (
    "⚠️ AVERTISSEMENT : Ce rapport est un outil d'aide à la décision généré "
    "automatiquement par intelligence artificielle. Il ne constitue pas une évaluation "
    "définitive du candidat et ne remplace en aucun cas le jugement professionnel d'un "
    "recruteur qualifié. La décision finale appartient exclusivement aux professionnels "
    "humains responsables du recrutement."
)

NON_SUBSTITUTION = (
    "🤝 Ce système IA est un outil d'assistance, non un décideur. Il analyse des données "
    "objectives mais ne peut évaluer la motivation, la personnalité ni la culture "
    "d'entreprise. L'entretien humain reste indispensable avant toute décision."
)


class RapportFinal(BaseModel):
    points_forts: list[str] = Field(default_factory=list, description="3-5 points forts du candidat pour CE poste")
    points_faibles: list[str] = Field(default_factory=list, description="3-5 lacunes ou points d'amélioration")
    adequation_poste: str = Field(..., description="Synthèse de l'adéquation (3-4 phrases)")
    recommandation: str = Field(..., description="'Entretien recommandé', 'À considérer', ou 'Profil insuffisant'")
    justification_recommandation: str = Field(..., description="Justification de la recommandation (2-3 phrases)")

    class Config:
        extra = "ignore"


RAPPORT_PROMPT = """\
Tu es un auditeur RH strict. Génère un rapport factuel basé UNIQUEMENT sur les scores et le matching ci-dessous.
N'INVENTE AUCUN point fort ou faible qui ne soit pas soutenu par les données fournies.

POSTE : {job_titre} chez {entreprise}
CANDIDAT : {nom_candidat}

SCORES :
  • Compétences techniques : {score_ct}/100 — {just_ct}
  • Expérience : {score_exp}/100 — {just_exp}
  • Formation : {score_form}/100 — {just_form}
  • Soft skills : {score_ss}/100 — {just_ss}
  • Score global pondéré : {score_global}/100

CORRESPONDANCES DES COMPÉTENCES :
{matching_summary}

GÉNÈRE :
1. 3 à 5 points forts CONCRETS pour ce poste (basés sur le CV)
2. 3 à 5 lacunes ou points d'amélioration importants
3. Synthèse de l'adéquation au poste (3-4 phrases professionnelles)
4. Recommandation :
   - "Entretien recommandé" si score global ≥ 70
   - "À considérer" si score global entre 50 et 69
   - "Profil insuffisant" si score global < 50
5. Justification de la recommandation (2-3 phrases)

Sois objectif, factuel et bienveillant. Réponds en JSON conforme au schéma.
"""


def _get_recommandation(score: float) -> str:
    if score >= 70:
        return "Entretien recommandé"
    elif score >= 50:
        return "À considérer"
    return "Profil insuffisant"


async def report_node(state: AnalysisState) -> dict:
    """Étape 4 : Génération du rapport final avec disclaimer."""
    logger.info(f"📝 [Nœud 4] Rapport | CV: {state['cv_id'][:8]}")

    job = state["job_description"]
    scores = state.get("scores") or {}
    skill_matches = state.get("skill_matches", [])
    cv_struct = state.get("cv_structure") or {}
    rag_scores = state.get("rag_scores") or {}
    justifications = scores.get("justifications", {})

    # Résumé du matching (max 8 compétences)
    matching_lines = [
        f"• {m.get('competence_requise', '?')}: [{m.get('niveau_match', '?').upper()}] — {m.get('justification', '')[:80]}"
        for m in skill_matches[:8]
    ]
    matching_summary = "\n".join(matching_lines) or "Non disponible"

    try:
        result = await invoke_structured(
            prompt_template=RAPPORT_PROMPT,
            variables={
                "job_titre": job.get("titre", "Non précisé"),
                "entreprise": job.get("entreprise") or "Non précisée",
                "nom_candidat": cv_struct.get("nom_complet") or "Candidat anonyme",
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
            "rag_scores": rag_scores,
            "points_forts": result.points_forts,
            "points_faibles": result.points_faibles,
            "correspondances_competences": skill_matches,
            "adequation_poste": result.adequation_poste,
            "recommandation": result.recommandation,
            "justification_recommandation": result.justification_recommandation,
            "explication_decision": scores.get("explication_decision", ""),
            "disclaimer": DISCLAIMER,
            "non_substitution": NON_SUBSTITUTION,
            "nom_candidat": cv_struct.get("nom_complet"),
            "titre_poste": job.get("titre"),
            "entreprise": job.get("entreprise"),
        }

        logger.info(
            f"✅ [Nœud 4] Rapport généré | "
            f"Score: {scores.get('score_global', 0):.1f} | {result.recommandation}"
        )
        return {"rapport": rapport, "guardrail_valide": False}

    except Exception as e:
        logger.error(f"❌ [Nœud 4] Erreur rapport: {e}")
        score_global = scores.get("score_global", 0)
        fallback = {
            "scores": scores,
            "rag_scores": rag_scores,
            "points_forts": ["Voir les détails du matching"],
            "points_faibles": ["Rapport partiel — erreur technique"],
            "correspondances_competences": skill_matches,
            "adequation_poste": f"Score calculé : {score_global:.1f}/100",
            "recommandation": _get_recommandation(score_global),
            "justification_recommandation": f"Score global : {score_global:.1f}/100",
            "explication_decision": "Calcul automatique de secours.",
            "disclaimer": DISCLAIMER,
            "non_substitution": NON_SUBSTITUTION,
        }
        return {"rapport": fallback, "guardrail_valide": False, "erreur": str(e)}
