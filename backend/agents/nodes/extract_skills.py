"""
Nœud 1 — Extraction des compétences et structuration du CV.
Utilise GroqCloud pour extraire de manière structurée les informations du CV.
"""
from loguru import logger
from typing import Optional
from pydantic import BaseModel, Field

from agents.state import AnalysisState
from services.llm import invoke_structured


# ── Schéma de sortie Pydantic ──────────────────────────────

class ExperienceItem(BaseModel):
    poste: str
    entreprise: str
    duree: Optional[str] = None
    description: Optional[str] = None

    class Config:
        extra = "ignore"




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
    niveau_formation: Optional[str] = None  # ex: "Bac+5", "Master", "Doctorat"
    domaine_formation: Optional[str] = None
    resume_profil: Optional[str] = None

    class Config:
        extra = "ignore"


# ── Prompt ────────────────────────────────────────────────

EXTRACTION_PROMPT = """
Tu es un auditeur RH strict, littéral et impartial. Ta seule tâche est d'évaluer le candidat en te basant EXCLUSIVEMENT sur le texte brut extrait de son CV fourni dans le contexte. N'INVENTE RIEN, NE DÉDUIS RIEN qui ne soit pas explicitement écrit.

CV à analyser :
---
{cv_text}
---

Extrais avec une précision absolue :
1. Les informations de contact (nom, email, téléphone)
2. Le titre professionnel actuel ou recherché (si mentionné)
3. Le nombre d'années d'expérience totales (approximatif, basé uniquement sur les dates)
4. Toutes les compétences techniques (langages, frameworks, outils, technologies) PRÉSENTES DANS LE TEXTE.
5. Les soft skills mentionnés explicitement (communication, leadership, travail en équipe, etc.)
6. Les langues parlées avec niveau si précisé
7. Les certifications et formations complémentaires trouvées
8. Le niveau et domaine de formation (Bac+2, Licence, Master, Doctorat, etc.)
9. Un résumé du profil en 2-3 phrases purement factuel.

Si une information est absente, laisse-la vide ou indique null. Ne fais aucune supposition.
Réponds en JSON conforme au schéma fourni.
"""


# ── Nœud LangGraph ────────────────────────────────────────

async def extract_skills_node(state: AnalysisState) -> dict:
    """
    Étape 1 du pipeline : Extraction structurée des compétences du CV.
    Met à jour l'état avec cv_structure, extracted_skills, soft_skills.
    """
    logger.info(f"🔍 [Nœud 1] Extraction des compétences | CV: {state['cv_id']}")

    try:
        extracted = await invoke_structured(
            prompt_template=EXTRACTION_PROMPT,
            variables={"cv_text": state["cv_text"][:6000]},
            output_schema=CVExtractedData,
            temperature=0.1,
        )

        cv_structure = extracted.model_dump()

        logger.info(
            f"✅ Compétences extraites: {len(extracted.competences_techniques)} tech, "
            f"{len(extracted.soft_skills)} soft skills"
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
            "cv_structure": {},
            "extracted_skills": [],
            "soft_skills": [],
            "erreur": f"Erreur extraction compétences: {str(e)}",
        }
