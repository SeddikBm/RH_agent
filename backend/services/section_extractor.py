"""
Service d'extraction de sections — LLM parse un CV ou une fiche de poste
en 4 sections normalisées pour l'indexation ChromaDB.

Sections normalisées :
  - competences : compétences techniques, outils, langages
  - experience  : expériences professionnelles, stages, projets
  - formation   : diplômes, certifications
  - profil      : soft skills, langues, résumé, objectif
"""
from loguru import logger
from pydantic import BaseModel, Field

from services.llm import invoke_structured


# ── Schémas de sortie ─────────────────────────────────────────

class CVSections(BaseModel):
    """4 sections normalisées extraites d'un CV."""
    competences: str = Field(default="", description="Compétences techniques, langages, frameworks, outils")
    experience: str = Field(default="", description="Expériences pro, stages, projets académiques/personnels")
    formation: str = Field(default="", description="Diplômes, certifications, formations suivies")
    profil: str = Field(default="", description="Soft skills, langues, résumé professionnel, objectif")

    class Config:
        extra = "ignore"


class JobSections(BaseModel):
    """4 sections normalisées extraites d'une fiche de poste."""
    competences: str = Field(default="", description="Compétences techniques requises et souhaitées")
    experience: str = Field(default="", description="Expérience requise, années, type de missions")
    formation: str = Field(default="", description="Formation requise, niveau de diplôme, domaine")
    profil: str = Field(default="", description="Qualités humaines, soft skills, langues requises")

    class Config:
        extra = "ignore"


# ── Prompts ───────────────────────────────────────────────────

CV_SECTIONS_PROMPT = """\
Tu es un parseur de CV expert. Lis attentivement le texte brut du CV ci-dessous
et extrais son contenu en 4 sections normalisées.

TEXTE DU CV :
---
{cv_text}
---

RÈGLES STRICTES :
1. Reproduis fidèlement le contenu — ne résume pas, ne modifie pas, n'invente rien.
2. Si une section est absente du CV, laisse-la vide ("").
3. Les soft skills et langues vont UNIQUEMENT dans "profil".
4. Les projets personnels et académiques vont dans "experience".
5. Les outils, technologies, langages, frameworks vont dans "competences".

Réponds en JSON strictement conforme au schéma.
"""

JOB_SECTIONS_PROMPT = """\
Tu es un parseur de fiche de poste expert. Extrais le contenu en 4 sections normalisées.

POSTE : {job_titre}
DESCRIPTION :
---
{job_text}
---
COMPÉTENCES REQUISES : {competences_requises}
COMPÉTENCES SOUHAITÉES : {competences_souhaitees}
FORMATION REQUISE : {formation_requise}
EXPÉRIENCE MINIMALE : {experience_min} ans

RÈGLES :
1. Section "competences" : toutes les compétences techniques requises ET souhaitées.
2. Section "experience" : type de missions attendues, années requises, contexte.
3. Section "formation" : niveau de diplôme, domaine, certifications demandées.
4. Section "profil" : qualités humaines, soft skills, langues requises.
5. Si une information est absente, laisse la section vide ("").

Réponds en JSON strictement conforme au schéma.
"""


# ── Fonctions d'extraction ────────────────────────────────────

async def extract_cv_sections(cv_text: str) -> dict[str, str]:
    """
    Parse un CV en 4 sections normalisées via LLM.
    Retourne un dict {section_name: content}.
    """
    logger.info("🔍 Extraction sections CV via LLM...")
    try:
        result = await invoke_structured(
            prompt_template=CV_SECTIONS_PROMPT,
            variables={"cv_text": cv_text[:7000]},
            output_schema=CVSections,
            temperature=0.0,
        )
        sections = {
            "competences": result.competences.strip(),
            "experience": result.experience.strip(),
            "formation": result.formation.strip(),
            "profil": result.profil.strip(),
        }
        non_empty = sum(1 for v in sections.values() if v)
        logger.info(f"✅ Sections CV extraites: {non_empty}/4 renseignées")
        return sections
    except Exception as e:
        logger.error(f"❌ Erreur extraction sections CV: {e}")
        # Fallback : tout le texte dans chaque section pour garantir le RAG
        return {
            "competences": cv_text[:2000],
            "experience": cv_text[:2000],
            "formation": cv_text[:1000],
            "profil": cv_text[:1000],
        }


async def extract_job_sections(job_data: dict) -> dict[str, str]:
    """
    Parse une fiche de poste en 4 sections normalisées via LLM.
    Fonctionne que ce soit depuis le formulaire ou un fichier uploadé.
    """
    logger.info(f"🔍 Extraction sections Job via LLM: {job_data.get('titre', '?')}")
    try:
        result = await invoke_structured(
            prompt_template=JOB_SECTIONS_PROMPT,
            variables={
                "job_titre": job_data.get("titre", ""),
                "job_text": job_data.get("description", "")[:5000],
                "competences_requises": ", ".join(job_data.get("competences_requises", [])),
                "competences_souhaitees": ", ".join(job_data.get("competences_souhaitees", [])),
                "formation_requise": job_data.get("formation_requise") or "Non précisée",
                "experience_min": job_data.get("annees_experience_min") or "Non précisé",
            },
            output_schema=JobSections,
            temperature=0.0,
        )
        sections = {
            "competences": result.competences.strip(),
            "experience": result.experience.strip(),
            "formation": result.formation.strip(),
            "profil": result.profil.strip(),
        }
        non_empty = sum(1 for v in sections.values() if v)
        logger.info(f"✅ Sections Job extraites: {non_empty}/4 renseignées")
        return sections
    except Exception as e:
        logger.error(f"❌ Erreur extraction sections Job: {e}")
        # Fallback structuré depuis les champs du formulaire
        desc = job_data.get("description", "")
        comps = ", ".join(job_data.get("competences_requises", []))
        return {
            "competences": comps or desc[:2000],
            "experience": f"{job_data.get('annees_experience_min', '')} ans d'expérience. {desc[:1000]}",
            "formation": job_data.get("formation_requise") or "",
            "profil": "",
        }
