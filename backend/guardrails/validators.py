"""
Garde-fous — Validation des rapports générés par le pipeline.
Assure la cohérence, l'intégrité et l'éthique du rapport.
"""
from typing import Literal
from loguru import logger

from agents.state import AnalysisState

MAX_RETRIES = 2

# ── Mots-clés sensibles à détecter ────────────────────────
MOTS_SENSIBLES = [
    "genre", "sexe", "âge", "religion", "nationalité", "origine",
    "handicap", "grossesse", "mariage", "orientation", "race",
    "couleur", "ethnie",
]


# ── Nœud de validation ────────────────────────────────────

async def validate_rapport_node(state: AnalysisState) -> dict:
    """
    Nœud garde-fou : Valide la structure et le contenu du rapport.
    - Vérifie la présence du disclaimer
    - Vérifie la cohérence des scores
    - Détecte les biais potentiels
    - Contrôle la structure minimale requise
    """
    rapport = state.get("rapport")
    tentatives = state.get("tentatives_retry", 0)

    if not rapport:
        logger.warning("⚠️ Rapport absent — retry demandé")
        return {
            "guardrail_valide": False,
            "tentatives_retry": tentatives + 1,
        }

    issues = []

    # ── 1. Vérification du disclaimer ─────────────────────
    disclaimer = rapport.get("disclaimer", "")
    if len(disclaimer) < 50:
        issues.append("Disclaimer absent ou trop court")
        rapport["disclaimer"] = (
            "⚠️ AVERTISSEMENT IMPORTANT : Ce rapport est un outil d'aide à la décision "
            "généré automatiquement. Il ne constitue pas une évaluation définitive et "
            "ne remplace en aucun cas le jugement professionnel d'un recruteur qualifié."
        )

    # ── 2. Vérification des scores ─────────────────────────
    scores = rapport.get("scores", {})
    required_scores = ["competences_techniques", "experience", "formation", "soft_skills", "score_global"]
    for score_key in required_scores:
        val = scores.get(score_key)
        if val is None:
            issues.append(f"Score manquant: {score_key}")
        elif not (0 <= float(val) <= 100):
            issues.append(f"Score hors bornes ({score_key}={val})")
            scores[score_key] = max(0, min(100, float(val)))

    # ── 3. Vérification de la structure minimale ──────────
    required_fields = ["points_forts", "points_faibles", "adequation_poste", "recommandation"]
    for field in required_fields:
        if not rapport.get(field):
            issues.append(f"Champ manquant: {field}")

    # ── 4. Vérification de la recommandation ──────────────
    # Toujours vérifier la cohérence score ↔ recommandation
    score_global = float(scores.get("score_global", 0))
    if score_global >= 70:
        expected_rec = "Entretien recommandé"
    elif score_global >= 50:
        expected_rec = "À considérer"
    else:
        expected_rec = "Profil insuffisant"

    current_rec = rapport.get("recommandation")
    recommandations_valides = {"Entretien recommandé", "À considérer", "Profil insuffisant"}
    if current_rec not in recommandations_valides or current_rec != expected_rec:
        rapport["recommandation"] = expected_rec
        if current_rec != expected_rec:
            issues.append(f"Recommandation corrigée: '{current_rec}' → '{expected_rec}' (score={score_global:.0f})")
    # ── 5. Détection de biais ──────────────────────────────
    texte_complet = " ".join([
        rapport.get("adequation_poste", ""),
        rapport.get("justification_recommandation", ""),
        " ".join(rapport.get("points_forts", [])),
        " ".join(rapport.get("points_faibles", [])),
    ]).lower()

    biais_detectes = [mot for mot in MOTS_SENSIBLES if mot in texte_complet]
    if biais_detectes:
        issues.append(f"⚠️ Mots sensibles détectés (biais potentiel): {biais_detectes}")
        rapport["avertissement_biais"] = (
            f"Attention : Le rapport contient des références à des critères potentiellement "
            f"discriminatoires ({', '.join(biais_detectes)}). Veuillez réviser manuellement."
        )

    if issues:
        logger.warning(f"⚠️ Garde-fous — {len(issues)} problème(s) détecté(s):")
        for issue in issues:
            logger.warning(f"   → {issue}")
    else:
        logger.info("✅ Garde-fous — Rapport validé sans problème")

    # Décision : retry si problèmes critiques et retries disponibles
    # "corrigée" couvre : recommandation invalide corrigée automatiquement
    critical_issues = [i for i in issues if "manquant" in i or "absent" in i or "corrigée" in i]
    should_retry = bool(critical_issues) and tentatives < MAX_RETRIES

    return {
        "rapport": rapport,
        "guardrail_valide": not should_retry,
        "tentatives_retry": tentatives + (1 if should_retry else 0),
    }


# ── Fonction de routage conditionnel ──────────────────────

def check_guardrail_result(
    state: AnalysisState,
) -> Literal["valid", "retry", "force_end"]:
    """
    Fonction de routage pour l'edge conditionnel du graphe.
    Détermine le prochain nœud selon le statut du garde-fou.
    """
    if state.get("guardrail_valide"):
        logger.info("✅ Routage → END (rapport validé)")
        return "valid"

    tentatives = state.get("tentatives_retry", 0)
    if tentatives >= MAX_RETRIES:
        logger.warning(f"⚠️ Routage → force_end (max retries atteint: {tentatives})")
        return "force_end"

    logger.info(f"🔄 Routage → retry (tentative {tentatives}/{MAX_RETRIES})")
    return "retry"
