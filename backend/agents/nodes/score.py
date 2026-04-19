"""
Nœud 3 — Scoring multicritère explicatif.
Calcule des scores par catégorie avec justification pour chaque note.
"""
from loguru import logger
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured


# ── Pondérations officielles ──────────────────────────────
POIDS = {
    "competences_techniques": 0.40,  # 40%
    "experience": 0.30,              # 30%
    "formation": 0.20,               # 20%
    "soft_skills": 0.10,             # 10%
}


# ── Schéma Pydantic ───────────────────────────────────────

class ScoringResult(BaseModel):
    score_competences_techniques: float = Field(..., ge=0, le=100)
    justification_competences: str
    score_experience: float = Field(..., ge=0, le=100)
    justification_experience: str
    score_formation: float = Field(..., ge=0, le=100)
    justification_formation: str
    score_soft_skills: float = Field(..., ge=0, le=100)
    justification_soft_skills: str

    class Config:
        extra = "ignore"


# ── Prompt ────────────────────────────────────────────────

SCORING_PROMPT = """
Tu es un expert RH chargé d'évaluer un candidat sur 4 critères.
Donne une note de 0 à 100 pour chaque critère avec une justification détaillée.

POSTE : {job_titre}
Compétences requises : {competences_requises}
Expérience minimale : {experience_min} ans
Formation requise : {formation_requise}

RÉSULTATS DU MATCHING :
{matching_summary}

Analyse de l'expérience : {experience_analysis}
Analyse de la formation : {formation_analysis}

GRILLE DE NOTATION :
- 90-100 : Critère parfaitement satisfait, dépasse les attentes
- 70-89  : Critère bien satisfait, quelques minor points
- 50-69  : Critère partiellement satisfait, lacunes comblables
- 30-49  : Critère insuffisant, lacunes significatives
- 0-29   : Critère non satisfait, problème majeur

Évalue chaque critère et justifie ta note en 2-3 phrases.
Réponds en JSON conforme au schéma.
"""


def _build_matching_summary(skill_matches: list[dict]) -> str:
    """Construit un résumé lisible des correspondances de compétences."""
    if not skill_matches:
        return "Aucune correspondance disponible."

    lines = []
    for m in skill_matches[:10]:  # Top 10 pour ne pas surcharger le prompt
        niveau = m.get("niveau_match", "inconnu")
        comp = m.get("competence_requise", "?")
        just = m.get("justification", "")
        lines.append(f"• {comp}: [{niveau.upper()}] — {just}")

    return "\n".join(lines)


def _compute_weighted_score(scores: dict) -> float:
    """Calcule le score global pondéré."""
    total = (
        scores["competences_techniques"] * POIDS["competences_techniques"]
        + scores["experience"] * POIDS["experience"]
        + scores["formation"] * POIDS["formation"]
        + scores["soft_skills"] * POIDS["soft_skills"]
    )
    return round(total, 1)


# ── Nœud LangGraph ────────────────────────────────────────

async def score_node(state: AnalysisState) -> dict:
    """
    Étape 3 du pipeline : Scoring multicritère explicatif.
    Produit des scores (0-100) avec justification pour chaque dimension.
    """
    logger.info(f"📊 [Nœud 3] Scoring | CV: {state['cv_id']}")

    job = state["job_description"]
    skill_matches = state.get("skill_matches", [])

    try:
        result = await invoke_structured(
            prompt_template=SCORING_PROMPT,
            variables={
                "job_titre": job.get("titre", "Non précisé"),
                "competences_requises": ", ".join(job.get("competences_requises", [])),
                "experience_min": job.get("annees_experience_min", "Non précisé"),
                "formation_requise": job.get("formation_requise", "Non précisé"),
                "matching_summary": _build_matching_summary(skill_matches),
                "experience_analysis": state.get("experience_analysis", "Non disponible"),
                "formation_analysis": state.get("formation_analysis", "Non disponible"),
            },
            output_schema=ScoringResult,
            temperature=0.1,
        )

        scores = {
            "competences_techniques": result.score_competences_techniques,
            "experience": result.score_experience,
            "formation": result.score_formation,
            "soft_skills": result.score_soft_skills,
            "justifications": {
                "competences_techniques": result.justification_competences,
                "experience": result.justification_experience,
                "formation": result.justification_formation,
                "soft_skills": result.justification_soft_skills,
            },
        }

        score_global = _compute_weighted_score(scores)
        scores["score_global"] = score_global

        logger.info(
            f"✅ Scores: CT={result.score_competences_techniques:.0f} | "
            f"EXP={result.score_experience:.0f} | "
            f"FORM={result.score_formation:.0f} | "
            f"SS={result.score_soft_skills:.0f} | "
            f"GLOBAL={score_global:.1f}"
        )

        return {"scores": scores}

    except Exception as e:
        logger.error(f"❌ [Nœud 3] Erreur scoring: {e}")
        # Fallback : scores basés sur le matching
        fallback_score = _fallback_score(skill_matches)
        return {
            "scores": fallback_score,
            "erreur": f"Scoring LLM échoué, score estimé: {str(e)}",
        }


def _fallback_score(skill_matches: list[dict]) -> dict:
    """Score de repli basé uniquement sur les correspondances."""
    if not skill_matches:
        base = 0.0
    else:
        niveau_scores = {
            "excellent": 100, "bon": 80, "partiel": 55, "faible": 30, "absent": 0
        }
        scores_list = [
            niveau_scores.get(m.get("niveau_match", "absent"), 0)
            for m in skill_matches
        ]
        base = sum(scores_list) / len(scores_list)

    return {
        "competences_techniques": base,
        "experience": base,
        "formation": base,
        "soft_skills": base,
        "score_global": base,
        "justifications": {
            "competences_techniques": "Score estimé à partir des correspondances.",
            "experience": "Score estimé.",
            "formation": "Score estimé.",
            "soft_skills": "Score estimé.",
        },
    }
