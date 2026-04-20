"""
LangGraph — Assemblage du workflow d'analyse RH.

Graphe :
  START → extract_skills → match_job → score → generate_report → validate_guardrail → END
"""
from loguru import logger
from langgraph.graph import StateGraph, START, END

from agents.state import AnalysisState
from agents.nodes.extract_skills import extract_skills_node
from agents.nodes.match_job import match_job_node
from agents.nodes.score import score_node
from agents.nodes.report import report_node
from guardrails.validators import validate_rapport_node, check_guardrail_result


def build_analysis_graph():
    """Construit et compile le graphe LangGraph d'analyse RH."""
    workflow = StateGraph(AnalysisState)

    workflow.add_node("extract_skills", extract_skills_node)
    workflow.add_node("match_job", match_job_node)
    workflow.add_node("score", score_node)
    workflow.add_node("generate_report", report_node)
    workflow.add_node("validate_guardrail", validate_rapport_node)

    workflow.add_edge(START, "extract_skills")
    workflow.add_edge("extract_skills", "match_job")
    workflow.add_edge("match_job", "score")
    workflow.add_edge("score", "generate_report")
    workflow.add_edge("generate_report", "validate_guardrail")

    workflow.add_conditional_edges(
        "validate_guardrail",
        check_guardrail_result,
        {"valid": END, "retry": "score", "force_end": END},
    )

    graph = workflow.compile()
    logger.info("✅ Graphe LangGraph compilé")
    return graph


analysis_graph = build_analysis_graph()


async def run_analysis(
    cv_id: str,
    job_id: str,
    cv_text: str,
    cv_structure: dict,
    job_description: dict,
    rag_scores: dict | None = None,
    section_contexts: dict | None = None,
) -> dict:
    """
    Lance une analyse complète via le pipeline LangGraph.
    cv_structure : structure déjà parsée du CV (évite un appel LLM supplémentaire).
    """
    initial_state: AnalysisState = {
        "cv_id": cv_id,
        "job_id": job_id,
        "cv_text": cv_text,
        "cv_structure": cv_structure or {},
        "job_description": job_description,
        "rag_scores": rag_scores or {},
        "section_contexts": section_contexts or {},
        "extracted_skills": [],
        "soft_skills": [],
        "skill_matches": [],
        "experience_analysis": None,
        "formation_analysis": None,
        "scores": None,
        "rapport": None,
        "erreur": None,
        "tentatives_retry": 0,
        "guardrail_valide": False,
    }

    logger.info(f"🧠 Pipeline LangGraph | CV: {cv_id[:8]} | Job: {job_id[:8]}")

    final_state = await analysis_graph.ainvoke(
        initial_state,
        config={"recursion_limit": 10},
    )

    logger.info(
        f"✅ Pipeline terminé | CV: {cv_id[:8]} | "
        f"Rapport: {'présent' if final_state.get('rapport') else 'absent'}"
    )
    return final_state
