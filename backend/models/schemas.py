"""
Modèles Pydantic — Schémas de données de l'application.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────

class StatutAnalyse(str, Enum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    ERREUR = "erreur"


class NiveauMatch(str, Enum):
    EXCELLENT = "excellent"
    BON = "bon"
    PARTIEL = "partiel"
    FAIBLE = "faible"
    ABSENT = "absent"


# ── CV ──────────────────────────────────────────────────────

class CVCreate(BaseModel):
    """Données retournées après upload et parsing d'un CV."""
    nom_fichier: str
    nom_candidat: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None


class CVStructure(BaseModel):
    """Structure extraite du CV par le LLM."""
    nom_complet: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    titre_professionnel: Optional[str] = None
    annees_experience: Optional[float] = None
    competences_techniques: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    langues: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    formations: list[dict] = Field(default_factory=list)
    experiences: list[dict] = Field(default_factory=list)
    resume_profil: Optional[str] = None


class CVResponse(BaseModel):
    """Réponse complète d'un CV."""
    id: UUID
    nom_fichier: str
    chemin_fichier: str
    texte_brut: str
    structure: Optional[CVStructure] = None
    date_upload: datetime
    taille_fichier: int

    class Config:
        from_attributes = True


# ── Fiche de Poste ──────────────────────────────────────────

class JobCreate(BaseModel):
    """Données pour créer une fiche de poste."""
    titre: str = Field(..., min_length=3, max_length=200)
    entreprise: Optional[str] = None
    description: str = Field(..., min_length=10)
    competences_requises: list[str] = Field(default_factory=list)
    competences_souhaitees: list[str] = Field(default_factory=list)
    annees_experience_min: Optional[int] = Field(None, ge=0, le=50)
    formation_requise: Optional[str] = None
    localisation: Optional[str] = None
    type_contrat: Optional[str] = None


class JobResponse(JobCreate):
    """Réponse complète d'une fiche de poste."""
    id: UUID
    date_creation: datetime
    date_modification: datetime

    class Config:
        from_attributes = True


# ── Analyse individuelle ─────────────────────────────────────

class AnalyseLancerRequest(BaseModel):
    """Requête pour lancer une analyse individuelle (1 CV + 1 Job)."""
    cv_id: UUID
    job_id: UUID


class CorrespondanceCompetence(BaseModel):
    """Résultat du matching pour une compétence donnée."""
    competence_requise: str
    niveau_match: NiveauMatch
    justification: str
    competence_cv: Optional[str] = None


class ScoresCategorie(BaseModel):
    """Scores par catégorie d'évaluation."""
    competences_techniques: float = Field(..., ge=0, le=100)
    experience: float = Field(..., ge=0, le=100)
    formation: float = Field(..., ge=0, le=100)
    soft_skills: float = Field(..., ge=0, le=100)
    score_global: float = Field(..., ge=0, le=100)


class RapportAnalyse(BaseModel):
    """Rapport d'analyse complet généré par le pipeline LangGraph."""
    scores: ScoresCategorie
    points_forts: list[str] = Field(default_factory=list)
    points_faibles: list[str] = Field(default_factory=list)
    correspondances_competences: list[CorrespondanceCompetence] = Field(default_factory=list)
    adequation_poste: str
    recommandation: str
    justification_recommandation: str
    explication_decision: Optional[str] = None   # Explication lisible du scoring
    disclaimer: str = (
        "⚠️ AVERTISSEMENT : Ce rapport est un outil d'aide à la décision uniquement. "
        "Il ne constitue pas une évaluation définitive d'un candidat et ne remplace "
        "en aucun cas le jugement d'un professionnel RH qualifié. La décision finale "
        "appartient exclusivement à l'équipe de recrutement humaine."
    )


class AnalyseResponse(BaseModel):
    """Réponse complète d'une analyse."""
    id: UUID
    cv_id: UUID
    job_id: UUID
    statut: StatutAnalyse
    rapport: Optional[RapportAnalyse] = None
    message_erreur: Optional[str] = None
    rag_scores: Optional[dict] = None
    rang: Optional[int] = None
    date_creation: datetime
    date_fin: Optional[datetime] = None
    duree_secondes: Optional[float] = None

    # Relations
    nom_candidat: Optional[str] = None
    titre_poste: Optional[str] = None

    class Config:
        from_attributes = True


class AnalyseListItem(BaseModel):
    """Élément de la liste des analyses."""
    id: UUID
    cv_id: UUID
    job_id: UUID
    statut: StatutAnalyse
    score_global: Optional[float] = None
    recommandation: Optional[str] = None
    nom_candidat: Optional[str] = None
    titre_poste: Optional[str] = None
    rang: Optional[int] = None
    date_creation: datetime

    class Config:
        from_attributes = True


# ── Batch Analyse ────────────────────────────────────────────

class BatchAnalyseLancerRequest(BaseModel):
    """Requête pour lancer une analyse batch (N CVs + 1 Job)."""
    job_id: UUID
    cv_ids: list[UUID] = Field(..., min_length=1)


class CandidateRanking(BaseModel):
    """Classement d'un candidat dans un batch."""
    rang: int
    cv_id: str
    nom_candidat: Optional[str] = None
    score_rag_global: float          # Score pondéré RAG (0-100)
    scores_sections: dict            # score par section {competences, experience, formation, profil}
    analyse_id: Optional[str] = None  # ID de l'analyse LangGraph si top 3


class BatchAnalyseResponse(BaseModel):
    """Réponse d'un batch d'analyse."""
    id: UUID
    job_id: UUID
    statut: str
    classement: list[CandidateRanking] = Field(default_factory=list)
    top3_analyses: list[AnalyseResponse] = Field(default_factory=list)
    date_creation: datetime
    date_fin: Optional[datetime] = None
