"""
Nœud 2 — Matching CV ↔ Fiche de poste via RAG + LLM.
Compare les compétences extraites avec les exigences du poste.
"""
from typing import Optional
from loguru import logger
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured


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
Tu es un auditeur RH strict, littéral et impartial. Ta seule tâche est d'évaluer le candidat en te basant EXCLUSIVEMENT sur le texte brut du CV fourni ci-dessous et la fiche de poste. N'INVENTE RIEN. N'utilise aucune information extérieure.

FICHE DE POSTE :
Titre: {job_titre}
Description: {job_description}
Compétences requises: {competences_requises}
Compétences souhaitées: {competences_souhaitees}
Expérience minimale requise: {experience_min} ans
Formation requise: {formation_requise}

TEXTE BRUT DU CV (source de vérité unique) :
---
{cv_text_brut}
---

COMPÉTENCES EXTRAITES DU CV :
Compétences techniques: {competences_cv}
Soft skills: {soft_skills}
Années d'expérience: {annees_experience}
Niveau de formation: {niveau_formation}
Domaine: {domaine_formation}

INSTRUCTIONS IMPORTANTES :
1. Base-toi UNIQUEMENT sur le texte brut du CV ci-dessus. Tout ce qui n'est pas mentionné explicitement dans ce texte est considéré comme ABSENT.
2. Pour chaque compétence REQUISE du poste, évalue le niveau de correspondance :
   - "excellent" : compétence présente et clairement maîtrisée dans le CV
   - "bon" : compétence présente mais avec une profondeur moindre
   - "partiel" : compétence partielle ou technologie connexe trouvée
   - "faible" : compétence vaguement mentionnée ou évoquée indirectement
   - "absent" : compétence totalement absente du CV
3. Analyse de l'expérience : Si la fiche de poste indique un STAGE (ex: PFE), ne pénalise pas pour l'absence d'expérience professionnelle. Les projets académiques et personnels sont valides.
4. Sois précis : "Outils de versioning (Git)" = match avec "Git" dans le CV.

Analyse l'adéquation globale de l'expérience et de la formation.
Réponds en JSON strictement conforme au schéma.
"""


# ── Nœud LangGraph ────────────────────────────────────────

async def match_job_node(state: AnalysisState) -> dict:
    """
    Étape 2 du pipeline : Matching sémantique CV ↔ Fiche de poste.
    Utilise directement le texte brut du CV (source de vérité) pour le matching.
    """
    logger.info(f"🔗 [Nœud 2] Matching CV ↔ Poste | CV: {state['cv_id']}")

    if state.get("erreur"):
        logger.warning("⚠️ Erreur détectée en amont, matching partiel")

    job = state["job_description"]
    cv_struct = state.get("cv_structure") or {}
    cv_text = state.get("cv_text", "")

    # ── Appel LLM avec le texte brut du CV ───────────────
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
                "cv_text_brut": cv_text[:4000],  # Texte brut complet du CV analysé
                "competences_cv": ", ".join(state.get("extracted_skills", [])),
                "soft_skills": ", ".join(state.get("soft_skills", [])),
                "annees_experience": cv_struct.get("annees_experience", "Non précisé"),
                "niveau_formation": cv_struct.get("niveau_formation", "Non précisé"),
                "domaine_formation": cv_struct.get("domaine_formation", "Non précisé"),
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
            "rag_context": [],
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

