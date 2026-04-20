"""
Nœud 2 — Matching CV ↔ Fiche de poste.
Source de vérité : texte brut du CV + RAG scores en contexte.
"""
from typing import Optional
from loguru import logger
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured


class SkillMatchItem(BaseModel):
    competence_requise: str
    niveau_match: str   # excellent | bon | partiel | faible | absent
    justification: str
    competence_cv: Optional[str] = None

    class Config:
        extra = "ignore"


class MatchingResult(BaseModel):
    correspondances: list[SkillMatchItem] = Field(default_factory=list)
    analyse_experience: str = ""
    analyse_formation: str = ""

    class Config:
        extra = "ignore"


MATCHING_PROMPT = """\
Tu es un auditeur RH strict. Évalue le candidat UNIQUEMENT sur la base du texte brut du CV fourni.
N'INVENTE RIEN. N'utilise aucune information extérieure au CV.

FICHE DE POSTE :
Titre : {job_titre}
Description : {job_description}
Compétences requises : {competences_requises}
Compétences souhaitées : {competences_souhaitees}
Expérience minimale : {experience_min} ans
Formation requise : {formation_requise}

TEXTE BRUT DU CV (source de vérité unique) :
---
{cv_text}
---

COMPÉTENCES EXTRAITES DU CV : {competences_cv}
SOFT SKILLS : {soft_skills}
EXPÉRIENCE DÉCLARÉE : {annees_experience} ans
FORMATION : {niveau_formation} en {domaine_formation}

SCORES RAG (similarité sémantique par section) :
  • Compétences : {rag_competences}/100
  • Expérience : {rag_experience}/100
  • Formation : {rag_formation}/100
  • Profil : {rag_profil}/100

INSTRUCTIONS :
1. Pour chaque compétence REQUISE du poste, évalue :
   - "excellent" : compétence clairement maîtrisée dans le CV
   - "bon" : compétence présente avec profondeur moindre
   - "partiel" : compétence partielle ou technologie connexe
   - "faible" : vaguement mentionné ou évoqué indirectement
   - "absent" : totalement absent du CV
2. Pour l'expérience : si le poste est un stage (PFE, stage), les projets académiques sont valides.
3. Sois littéral : seul ce qui est écrit dans le CV compte.

Réponds en JSON conforme au schéma.
"""


async def match_job_node(state: AnalysisState) -> dict:
    """Étape 2 : Matching sémantique CV ↔ Fiche de poste."""
    logger.info(f"🔗 [Nœud 2] Matching | CV: {state['cv_id'][:8]}")

    job = state["job_description"]
    cv_struct = state.get("cv_structure") or {}
    rag_scores = state.get("rag_scores") or {}

    try:
        result = await invoke_structured(
            prompt_template=MATCHING_PROMPT,
            variables={
                "job_titre": job.get("titre", "Non précisé"),
                "job_description": job.get("description", "")[:2000],
                "competences_requises": ", ".join(job.get("competences_requises", [])),
                "competences_souhaitees": ", ".join(job.get("competences_souhaitees", [])),
                "experience_min": job.get("annees_experience_min") or "Non précisé",
                "formation_requise": job.get("formation_requise") or "Non précisé",
                "cv_text": state.get("cv_text", "")[:4000],
                "competences_cv": ", ".join(state.get("extracted_skills", [])),
                "soft_skills": ", ".join(state.get("soft_skills", [])),
                "annees_experience": cv_struct.get("annees_experience") or "Non précisé",
                "niveau_formation": cv_struct.get("niveau_formation") or "Non précisé",
                "domaine_formation": cv_struct.get("domaine_formation") or "Non précisé",
                "rag_competences": round(rag_scores.get("competences", 0)),
                "rag_experience": round(rag_scores.get("experience", 0)),
                "rag_formation": round(rag_scores.get("formation", 0)),
                "rag_profil": round(rag_scores.get("profil", 0)),
            },
            output_schema=MatchingResult,
            temperature=0.1,
        )

        skill_matches = [m.model_dump() for m in result.correspondances]
        logger.info(f"✅ [Nœud 2] {len(skill_matches)} compétences évaluées")

        return {
            "skill_matches": skill_matches,
            "experience_analysis": result.analyse_experience,
            "formation_analysis": result.analyse_formation,
        }

    except Exception as e:
        logger.error(f"❌ [Nœud 2] Erreur matching: {e}")
        return {
            "skill_matches": [],
            "experience_analysis": "",
            "formation_analysis": "",
            "erreur": f"Erreur matching: {str(e)}",
        }
