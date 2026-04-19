"""
LangGraph — Définition de l'état du pipeline d'analyse.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


class AnalysisState(TypedDict):
    """
    État partagé entre tous les nœuds du pipeline LangGraph.
    Contient toutes les données nécessaires à l'analyse complète.
    """

    # ── Entrées ───────────────────────────────────────────
    cv_id: str                          # UUID du CV
    job_id: str                         # UUID de la fiche de poste
    cv_text: str                        # Texte brut du CV
    job_description: dict               # Données de la fiche de poste

    # ── Résultats intermédiaires ──────────────────────────
    cv_structure: Optional[dict]        # CV parsé et structuré (Étape 1)
    extracted_skills: list[str]         # Compétences extraites du CV
    soft_skills: list[str]              # Soft skills du candidat
    rag_context: list[str]              # Contexte RAG pertinent

    # ── Résultats du matching (Étape 2) ──────────────────
    skill_matches: list[dict]           # Correspondances compétence par compétence
    experience_analysis: Optional[str]  # Analyse de l'expérience
    formation_analysis: Optional[str]   # Analyse de la formation

    # ── Scores (Étape 3) ──────────────────────────────────
    scores: Optional[dict]              # Scores par catégorie + global

    # ── Rapport final (Étape 4) ───────────────────────────
    rapport: Optional[dict]             # Rapport complet structuré

    # ── Contrôle du workflow ──────────────────────────────
    erreur: Optional[str]               # Message d'erreur si échec
    tentatives_retry: int               # Nombre de tentatives de retry
    guardrail_valide: bool              # True si le rapport est valide
