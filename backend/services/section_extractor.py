"""
Service d'extraction de sections — LLM parse un CV ou une fiche de poste
en 4 sections normalisées pour l'indexation ChromaDB.

Sections normalisées :
  - competences : compétences techniques, outils, langages
  - experience  : expériences professionnelles, stages, projets
  - formation   : diplômes, certifications
  - profil      : soft skills, langues, résumé, objectif

OPTIMISATION RAG : Les sections CV sont formatées dans un style proche des fiches de poste
pour maximiser la similarité cosine lors du matching.
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
Tu es un expert RH. Analyse le CV ci-dessous et reformule son contenu en 4 sections structurées
dans un format semblable à une fiche de poste (listes descriptives, mots-clés techniques).
L'objectif est que ces sections puissent être comparées sémantiquement avec des fiches de poste.

TEXTE DU CV :
---
{cv_text}
---

INSTRUCTIONS STRICTES :
1. Section "competences" : Liste TOUTES les compétences techniques, langages, frameworks, outils, technologies
   mentionnés dans le CV. Format : liste séparée par des virgules + phrases descriptives.
   Exemple: "Python, SQL, Django, REST API. Maîtrise du développement backend et des bases de données relationnelles."

2. Section "experience" : Résume les expériences professionnelles, stages et projets.
   Inclure : durée totale, types de missions effectuées, secteurs, responsabilités.
   Format : phrases structurées décrivant le type de travail accompli.

3. Section "formation" : Diplômes, niveau d'études, domaines, certifications.
   Format : "Master/Licence/Bac+X en [domaine], [établissement], [année]"

4. Section "profil" : Soft skills, qualités, langues parlées, niveau de langue, objectifs professionnels.
   Format : liste de qualités + phrases sur l'objectif.

5. Si une information est absente, laisse la section vide ("").
6. N'invente RIEN - utilise uniquement ce qui est dans le CV.

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

INSTRUCTIONS :
1. Section "competences" : Liste TOUTES les compétences techniques requises ET souhaitées.
   Format : liste séparée par des virgules + phrases descriptives des besoins techniques.
   Exemple: "Python, SQL, Django, REST API. Maîtrise du développement backend requise."

2. Section "experience" : Type de missions attendues, années requises, contexte du poste.
   Format : phrases décrivant précisément l'expérience attendue.

3. Section "formation" : Niveau de diplôme, domaine, certifications demandées.
   Format : "Bac+X en [domaine]" + certifications requises.

4. Section "profil" : Qualités humaines, soft skills, langues requises avec niveau.
   Format : liste de qualités + langues.

5. Si une information est absente, laisse la section vide ("").

Réponds en JSON strictement conforme au schéma.
"""


# ── Fonctions d'extraction ────────────────────────────────────

async def extract_cv_sections(cv_text: str) -> dict[str, str]:
    """
    Parse un CV en 4 sections normalisées via LLM.
    Retourne un dict {section_name: content}.
    Les sections sont formatées pour maximiser la similarité RAG avec les jobs.
    """
    logger.info("🔍 Extraction sections CV via LLM (format structuré)...")
    try:
        result = await invoke_structured(
            prompt_template=CV_SECTIONS_PROMPT,
            variables={"cv_text": cv_text[:10000]},
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
        # Fallback structuré : extraire les informations clés du texte brut
        return _fallback_cv_sections(cv_text)


def _fallback_cv_sections(cv_text: str) -> dict[str, str]:
    """Fallback : sections basiques extraites du texte brut sans LLM."""
    import re

    # Tentative d'extraire des mots-clés techniques communs
    tech_keywords = re.findall(
        r'\b(Python|Java|JavaScript|TypeScript|React|Node|SQL|PostgreSQL|MySQL|'
        r'MongoDB|Docker|Kubernetes|AWS|Git|Linux|FastAPI|Django|Flask|'
        r'Machine Learning|Deep Learning|TensorFlow|PyTorch|Pandas|NumPy)\b',
        cv_text, re.IGNORECASE
    )
    competences = ", ".join(set(tech_keywords)) if tech_keywords else cv_text[:2000]

    return {
        "competences": competences,
        "experience": cv_text[1000:3000] if len(cv_text) > 1000 else cv_text[:2000],
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
