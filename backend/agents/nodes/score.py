"""
Nœud 3 — Scoring multicritère explicatif.
Combine le score LLM et le score RAG pour un score hybride.
"""
from loguru import logger
from pydantic import BaseModel, Field
from typing import Optional

from agents.state import AnalysisState
from services.llm import invoke_structured

# ── Pondérations ──────────────────────────────────────────────
POIDS = {
    "competences_techniques": 0.40,
    "experience": 0.30,
    "formation": 0.20,
    "soft_skills": 0.10,
}

# Poids du RAG (30% RAG, 70% LLM)
RAG_WEIGHT = 0.30


class ScoringResult(BaseModel):
    score_competences_techniques: float = Field(..., ge=0, le=100)
    justification_competences: str
    score_experience: float = Field(..., ge=0, le=100)
    justification_experience: str
    score_formation: float = Field(..., ge=0, le=100)
    justification_formation: str
    score_soft_skills: float = Field(..., ge=0, le=100)
    justification_soft_skills: str
    explication_decision: str = Field(default="", description="Synthèse du scoring en 2-3 phrases")

    class Config:
        extra = "ignore"


SCORING_PROMPT = """\
Tu es un expert RH. Note le candidat sur 4 critères (0 à 100), avec justification.

POSTE : {job_titre}
Compétences requises : {competences_requises}
Expérience minimale : {experience_min} ans
Formation requise : {formation_requise}

RÉSULTATS DU MATCHING :
{matching_summary}

Analyse expérience : {experience_analysis}
Analyse formation : {formation_analysis}

SCORES RAG (similarité sémantique, 0-100) :
  • Compétences : {rag_competences}/100
  • Expérience : {rag_experience}/100
  • Formation : {rag_formation}/100
  • Soft skills : {rag_profil}/100

GRILLE DE NOTATION :
  90-100 : Critère parfaitement satisfait
  70-89  : Bien satisfait, quelques points mineurs
  50-69  : Partiellement satisfait
  30-49  : Insuffisant, lacunes significatives
  0-29   : Non satisfait, problème majeur

Donne une note et une justification (2-3 phrases) pour chaque critère.
Fournis aussi une explication_decision (synthèse globale en 2-3 phrases).
Réponds en JSON conforme au schéma.
"""


def _matching_summary(skill_matches: list[dict]) -> str:
    if not skill_matches:
        return "Aucune correspondance disponible."
    lines = []
    for m in skill_matches[:10]:
        niveau = m.get("niveau_match", "inconnu").upper()
        comp = m.get("competence_requise", "?")
        just = m.get("justification", "")[:80]
        lines.append(f"• {comp}: [{niveau}] — {just}")
    return "\n".join(lines)


def _compute_weighted_score(scores: dict) -> float:
    return round(
        scores["competences_techniques"] * POIDS["competences_techniques"]
        + scores["experience"] * POIDS["experience"]
        + scores["formation"] * POIDS["formation"]
        + scores["soft_skills"] * POIDS["soft_skills"],
        1,
    )


def _blend_with_rag(llm_scores: dict, rag_scores: Optional[dict]) -> dict:
    """Score final = 70% LLM + 30% RAG pour chaque catégorie."""
    if not rag_scores:
        return llm_scores

    rag_map = {
        "competences_techniques": rag_scores.get("competences", 0),
        "experience": rag_scores.get("experience", 0),
        "formation": rag_scores.get("formation", 0),
        "soft_skills": rag_scores.get("profil", 0),
    }

    return {
        k: round((1 - RAG_WEIGHT) * llm_scores[k] + RAG_WEIGHT * rag_map[k], 1)
        for k in llm_scores
    }


async def score_node(state: AnalysisState) -> dict:
    """Étape 3 : Scoring multicritère avec justification."""
    logger.info(f"📊 [Nœud 3] Scoring | CV: {state['cv_id'][:8]}")

    job = state["job_description"]
    skill_matches = state.get("skill_matches", [])
    rag_scores = state.get("rag_scores") or {}

    try:
        result = await invoke_structured(
            prompt_template=SCORING_PROMPT,
            variables={
                "job_titre": job.get("titre", "Non précisé"),
                "competences_requises": ", ".join(job.get("competences_requises", [])),
                "experience_min": job.get("annees_experience_min") or "Non précisé",
                "formation_requise": job.get("formation_requise") or "Non précisé",
                "matching_summary": _matching_summary(skill_matches),
                "experience_analysis": state.get("experience_analysis") or "Non disponible",
                "formation_analysis": state.get("formation_analysis") or "Non disponible",
                "rag_competences": round(rag_scores.get("competences", 0)),
                "rag_experience": round(rag_scores.get("experience", 0)),
                "rag_formation": round(rag_scores.get("formation", 0)),
                "rag_profil": round(rag_scores.get("profil", 0)),
            },
            output_schema=ScoringResult,
            temperature=0.1,
        )

        llm_scores = {
            "competences_techniques": result.score_competences_techniques,
            "experience": result.score_experience,
            "formation": result.score_formation,
            "soft_skills": result.score_soft_skills,
        }

        final_scores = _blend_with_rag(llm_scores, rag_scores)
        score_global = _compute_weighted_score(final_scores)

        scores = {
            **final_scores,
            "score_global": score_global,
            "justifications": {
                "competences_techniques": result.justification_competences,
                "experience": result.justification_experience,
                "formation": result.justification_formation,
                "soft_skills": result.justification_soft_skills,
            },
            "explication_decision": result.explication_decision,
        }

        logger.info(
            f"✅ [Nœud 3] Score global: {score_global:.1f} | "
            f"CT={final_scores['competences_techniques']:.0f} | "
            f"EXP={final_scores['experience']:.0f} | "
            f"FORM={final_scores['formation']:.0f}"
        )
        return {"scores": scores}

    except Exception as e:
        logger.error(f"❌ [Nœud 3] Erreur scoring: {e}")
        fallback = _fallback_score(skill_matches, rag_scores)
        return {"scores": fallback, "erreur": f"Scoring LLM échoué: {str(e)}"}


def _fallback_score(skill_matches: list[dict], rag_scores: Optional[dict] = None) -> dict:
    """Score de secours basé sur le matching et/ou le RAG."""
    if skill_matches:
        niveau_scores = {"excellent": 100, "bon": 80, "partiel": 55, "faible": 30, "absent": 0}
        scores_list = [niveau_scores.get(m.get("niveau_match", "absent"), 0) for m in skill_matches]
        base = sum(scores_list) / len(scores_list)
    elif rag_scores:
        base = rag_scores.get("competences", 0) * 0.4 + rag_scores.get("experience", 0) * 0.3
    else:
        base = 0.0

    return {
        "competences_techniques": base,
        "experience": base,
        "formation": base,
        "soft_skills": base,
        "score_global": base,
        "explication_decision": "Score estimé automatiquement suite à une erreur technique.",
        "justifications": {
            "competences_techniques": "Score estimé.",
            "experience": "Score estimé.",
            "formation": "Score estimé.",
            "soft_skills": "Score estimé.",
        },
    }
