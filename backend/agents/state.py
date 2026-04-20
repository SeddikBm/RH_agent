"""
LangGraph — État du pipeline d'analyse RH.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


class AnalysisState(TypedDict):
    """État partagé entre tous les nœuds du pipeline LangGraph."""

    # ── Entrées ──────────────────────────────────────────────
    cv_id: str
    job_id: str
    cv_text: str
    cv_structure: dict          # Structure pré-parsée du CV (depuis la DB)
    job_description: dict

    # ── Contexte RAG ─────────────────────────────────────────
    rag_scores: Optional[dict]          # Scores de similarité par section
    section_contexts: Optional[dict]    # Textes des sections CV (pour le prompt)

    # ── Résultats intermédiaires ─────────────────────────────
    extracted_skills: list[str]
    soft_skills: list[str]

    # ── Résultats du matching ─────────────────────────────────
    skill_matches: list[dict]
    experience_analysis: Optional[str]
    formation_analysis: Optional[str]

    # ── Scores ───────────────────────────────────────────────
    scores: Optional[dict]

    # ── Rapport final ─────────────────────────────────────────
    rapport: Optional[dict]

    # ── Contrôle du workflow ──────────────────────────────────
    erreur: Optional[str]
    tentatives_retry: int
    guardrail_valide: bool
