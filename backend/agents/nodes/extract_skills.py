"""
Nœud 1 — Extraction des compétences et structuration du CV.

Optimisation : si cv_structure est déjà présent dans l'état (parsé à l'upload),
on le réutilise directement sans appel LLM supplémentaire.
"""
from loguru import logger
from typing import Optional
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured


class CVExtractedData(BaseModel):
    nom_complet: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    titre_professionnel: Optional[str] = None
    annees_experience: Optional[float] = None
    competences_techniques: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    langues: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    niveau_formation: Optional[str] = None
    domaine_formation: Optional[str] = None
    resume_profil: Optional[str] = None

    class Config:
        extra = "ignore"


EXTRACTION_PROMPT = """\
Tu es un auditeur RH strict. Extrais les informations du CV ci-dessous.
N'INVENTE RIEN — si une information est absente, laisse-la vide (null ou []).

CV :
---
{cv_text}
---

Extrais :
1. Informations de contact (nom, email, téléphone)
2. Titre professionnel
3. Années d'expérience totales (basé sur les dates)
4. Toutes les compétences techniques présentes dans le texte
5. Soft skills mentionnés explicitement
6. Langues parlées
7. Certifications et formations complémentaires
8. Niveau et domaine de formation (Bac+2, Master, etc.)
9. Résumé factuel du profil en 2-3 phrases

Réponds en JSON conforme au schéma.
"""


async def extract_skills_node(state: AnalysisState) -> dict:
    """
    Étape 1 : Extraction des compétences du CV.
    Réutilise cv_structure si déjà disponible (uploadé et parsé).
    """
    logger.info(f"🔍 [Nœud 1] Extraction compétences | CV: {state['cv_id'][:8]}")

    # ── Réutiliser la structure existante si disponible ───────
    existing = state.get("cv_structure") or {}
    if existing and existing.get("competences_techniques") is not None:
        logger.info("✅ [Nœud 1] Structure CV réutilisée (pas d'appel LLM)")
        return {
            "extracted_skills": existing.get("competences_techniques", []),
            "soft_skills": existing.get("soft_skills", []),
            "erreur": None,
        }

    # ── Sinon : appel LLM pour extraire ──────────────────────
    try:
        extracted = await invoke_structured(
            prompt_template=EXTRACTION_PROMPT,
            variables={"cv_text": state["cv_text"][:6000]},
            output_schema=CVExtractedData,
            temperature=0.0,
        )

        cv_structure = extracted.model_dump()
        logger.info(
            f"✅ [Nœud 1] Compétences extraites: "
            f"{len(extracted.competences_techniques)} tech, {len(extracted.soft_skills)} soft"
        )

        return {
            "cv_structure": cv_structure,
            "extracted_skills": extracted.competences_techniques,
            "soft_skills": extracted.soft_skills,
            "erreur": None,
        }

    except Exception as e:
        logger.error(f"❌ [Nœud 1] Erreur extraction: {e}")
        return {
            "extracted_skills": [],
            "soft_skills": [],
            "erreur": f"Erreur extraction compétences: {str(e)}",
        }
