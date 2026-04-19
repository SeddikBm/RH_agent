"""
Nœud 2 — Matching CV ↔ Fiche de poste via RAG + LLM.
Compare les compétences extraites avec les exigences du poste.
"""
from typing import Optional
from loguru import logger
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured
from services.rag import get_relevant_context


# ── Schémas Pydantic ──────────────────────────────────────

class SkillMatchItem(BaseModel):
    competence_requise: str
    niveau_match: str  # "excellent", "bon", "partiel", "faible", "absent"
    justification: str
    competence_cv: Optional[str] = None

    class Config:
        extra = "ignore"


class MatchingResult(BaseModel):
    correspondances: list[SkillMatchItem] = Field(default_factory=list)
    analyse_experience: str = ""
    analyse_formation: str = ""
    points_forts_matching: list[str] = Field(default_factory=list)
    lacunes_principales: list[str] = Field(default_factory=list)

    class Config:
        extra = "ignore"


# ── Prompt ────────────────────────────────────────────────

MATCHING_PROMPT = """
Tu es un expert RH. Compare ce CV avec la fiche de poste suivante.

FICHE DE POSTE :
Titre: {job_titre}
Description: {job_description}
Compétences requises: {competences_requises}
Compétences souhaitées: {competences_souhaitees}
Expérience minimale requise: {experience_min} ans
Formation requise: {formation_requise}

PROFIL DU CANDIDAT (extrait du CV) :
Compétences techniques: {competences_cv}
Soft skills: {soft_skills}
Années d'expérience: {annees_experience}
Niveau de formation: {niveau_formation}
Domaine: {domaine_formation}

CONTEXTE ADDITIONNEL (RAG) :
{rag_context}

Pour chaque compétence REQUISE du poste, évalue le niveau de correspondance :
- "excellent" : compétence présente et maîtrisée
- "bon" : compétence présente mais développement possible
- "partiel" : compétence partielle ou connexe
- "faible" : compétence mentionnée mais peu développée
- "absent" : compétence absente du CV

Analyse aussi l'adéquation de l'expérience et de la formation.
Réponds en JSON conforme au schéma.
"""


# ── Nœud LangGraph ────────────────────────────────────────

async def match_job_node(state: AnalysisState) -> dict:
    """
    Étape 2 du pipeline : Matching sémantique CV ↔ Fiche de poste.
    Utilise le RAG pour enrichir le contexte avant l'appel LLM.
    """
    logger.info(f"🔗 [Nœud 2] Matching CV ↔ Poste | CV: {state['cv_id']}")

    if state.get("erreur"):
        logger.warning("⚠️ Erreur détectée en amont, matching partiel")

    job = state["job_description"]
    cv_struct = state.get("cv_structure") or {}

    # ── Enrichissement RAG ────────────────────────────────
    try:
        rag_results = await get_relevant_context(
            query=f"{job.get('titre', '')} {' '.join(job.get('competences_requises', []))}",
            collection_name="cvs",
            top_k=3,
        )
        rag_context = "\n---\n".join(rag_results[:2]) if rag_results else "Aucun contexte additionnel."
    except Exception:
        rag_context = "RAG non disponible."

    # ── Appel LLM ────────────────────────────────────────
    try:
        result = await invoke_structured(
            prompt_template=MATCHING_PROMPT,
            variables={
                "job_titre": job.get("titre", "Non précisé"),
                "job_description": job.get("description", "")[:2000],
                "competences_requises": ", ".join(job.get("competences_requises", [])),
                "competences_souhaitees": ", ".join(job.get("competences_souhaitees", [])),
                "experience_min": job.get("annees_experience_min", "Non précisé"),
                "formation_requise": job.get("formation_requise", "Non précisé"),
                "competences_cv": ", ".join(state.get("extracted_skills", [])),
                "soft_skills": ", ".join(state.get("soft_skills", [])),
                "annees_experience": cv_struct.get("annees_experience", "Non précisé"),
                "niveau_formation": cv_struct.get("niveau_formation", "Non précisé"),
                "domaine_formation": cv_struct.get("domaine_formation", "Non précisé"),
                "rag_context": rag_context[:1500],
            },
            output_schema=MatchingResult,
            temperature=0.1,
        )

        skill_matches = [m.model_dump() for m in result.correspondances]

        logger.info(f"✅ Matching terminé: {len(skill_matches)} compétences évaluées")

        return {
            "skill_matches": skill_matches,
            "experience_analysis": result.analyse_experience,
            "formation_analysis": result.analyse_formation,
            "rag_context": rag_results if rag_results else [],
        }

    except Exception as e:
        logger.error(f"❌ [Nœud 2] Erreur matching: {e}")
        return {
            "skill_matches": [],
            "experience_analysis": "",
            "formation_analysis": "",
            "rag_context": [],
            "erreur": f"Erreur matching: {str(e)}",
        }
