"""Routes Analyses — Batch multi-CV et export PDF."""
import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import AnalyseModel, BatchAnalyseModel, CVModel, JobModel, get_db
from models.schemas import (
    AnalyseLancerRequest, AnalyseResponse, BatchAnalyseLancerRequest,
    RapportAnalyse, ScoresCategorie, CorrespondanceCompetence, NiveauMatch,
    CandidateRanking,
)
from agents.graph import run_analysis

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────

def _build_analyse_response(
    analyse: AnalyseModel,
    cv: Optional[CVModel],
    job: Optional[JobModel],
) -> AnalyseResponse:
    nom_candidat = None
    if cv and cv.structure:
        nom_candidat = cv.structure.get("nom_complet")
    elif cv:
        nom_candidat = cv.nom_fichier

    rapport_obj = None
    if analyse.rapport:
        r = analyse.rapport
        scores = r.get("scores", {})
        try:
            rapport_obj = RapportAnalyse(
                scores=ScoresCategorie(
                    competences_techniques=scores.get("competences_techniques", 0),
                    experience=scores.get("experience", 0),
                    formation=scores.get("formation", 0),
                    soft_skills=scores.get("soft_skills", 0),
                    score_global=scores.get("score_global", 0),
                ),
                points_forts=r.get("points_forts", []),
                points_faibles=r.get("points_faibles", []),
                correspondances_competences=[
                    CorrespondanceCompetence(
                        competence_requise=m.get("competence_requise", ""),
                        niveau_match=NiveauMatch(m.get("niveau_match", "absent")),
                        justification=m.get("justification", ""),
                        competence_cv=m.get("competence_cv"),
                    )
                    for m in r.get("correspondances_competences", [])
                ],
                adequation_poste=r.get("adequation_poste", ""),
                recommandation=r.get("recommandation", ""),
                justification_recommandation=r.get("justification_recommandation", ""),
                explication_decision=r.get("explication_decision"),
                disclaimer=r.get("disclaimer", ""),
            )
        except Exception as e:
            logger.warning(f"⚠️ Impossible de parser le rapport: {e}")

    return AnalyseResponse(
        id=analyse.id,
        cv_id=analyse.cv_id,
        job_id=analyse.job_id,
        statut=analyse.statut,
        rapport=rapport_obj,
        message_erreur=analyse.message_erreur,
        rag_scores=analyse.rag_scores,
        rang=analyse.rang,
        date_creation=analyse.date_creation,
        date_fin=analyse.date_fin,
        duree_secondes=analyse.duree_secondes,
        nom_candidat=nom_candidat,
        titre_poste=job.titre if job else None,
    )


# ══════════════════════════════════════════════════════════════
# BATCH ANALYSE : N CVs × 1 Job
# ══════════════════════════════════════════════════════════════

@router.post("/run-batch", status_code=status.HTTP_202_ACCEPTED)
async def lancer_batch_analyse(
    request: BatchAnalyseLancerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Lance une analyse batch : N CVs vs 1 fiche de poste.
    1. RAG section par section → classement de tous les CVs
    2. Top 3 → pipeline LangGraph complet pour chacun
    Retourne immédiatement le batch_id pour polling.
    """
    # Vérifier le job
    job_result = await db.execute(select(JobModel).where(JobModel.id == request.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    # Vérifier les CVs
    cv_ids_str = [str(cid) for cid in request.cv_ids]
    cv_results = await db.execute(select(CVModel).where(CVModel.id.in_(request.cv_ids)))
    cvs = {str(cv.id): cv for cv in cv_results.scalars().all()}

    missing = [cid for cid in cv_ids_str if cid not in cvs]
    if missing:
        raise HTTPException(status_code=404, detail=f"CVs non trouvés: {missing}")

    # Vérifier que les CVs sont indexés (sections présentes)
    not_indexed = [cid for cid in cv_ids_str if not cvs[cid].sections]
    if not_indexed:
        logger.warning(
            f"⚠️ {len(not_indexed)} CV(s) pas encore indexés — l'indexation est peut-être en cours"
        )

    # Créer le batch
    batch_id = uuid.uuid4()
    batch = BatchAnalyseModel(
        id=batch_id,
        job_id=request.job_id,
        statut="en_cours",
        cv_ids_soumis=cv_ids_str,
        date_creation=datetime.utcnow(),
    )
    db.add(batch)
    await db.flush()

    job_data = {
        "titre": job.titre,
        "entreprise": job.entreprise,
        "description": job.description,
        "competences_requises": job.competences_requises or [],
        "competences_souhaitees": job.competences_souhaitees or [],
        "annees_experience_min": job.annees_experience_min,
        "formation_requise": job.formation_requise,
    }

    logger.info(f"🚀 Batch lancé: {batch_id} | Job: {job.titre} | {len(cv_ids_str)} CVs")

    background_tasks.add_task(
        _execute_batch,
        batch_id=str(batch_id),
        job_id=str(request.job_id),
        cv_ids=cv_ids_str,
        job_data=job_data,
    )

    return {"batch_id": str(batch_id), "statut": "en_cours", "nb_cvs": len(cv_ids_str)}


async def _execute_batch(
    batch_id: str,
    job_id: str,
    cv_ids: list[str],
    job_data: dict,
):
    """Exécute le batch complet en arrière-plan."""
    from models.database import AsyncSessionLocal
    from services.rag import get_top_k_candidates

    start_time = datetime.utcnow()

    async with AsyncSessionLocal() as db:
        try:
            # ── 1. RAG : classer tous les CVs ──────────────────
            ranking, top3 = get_top_k_candidates(job_id, cv_ids, top_k=3)

            # Sauvegarder le classement
            batch_result = await db.execute(
                select(BatchAnalyseModel).where(BatchAnalyseModel.id == uuid.UUID(batch_id))
            )
            batch = batch_result.scalar_one()
            batch.classement = ranking
            batch.top3_cv_ids = [r["cv_id"] for r in top3]
            await db.flush()

            logger.info(f"📊 RAG terminé | Top 3: {[r['cv_id'][:8] for r in top3]}")

            # ── 2. LangGraph pour le top 3 ─────────────────────
            analyse_tasks = []
            for item in top3:
                cv_result = await db.execute(
                    select(CVModel).where(CVModel.id == uuid.UUID(item["cv_id"]))
                )
                cv = cv_result.scalar_one_or_none()
                if not cv:
                    continue

                analyse_id = uuid.uuid4()
                analyse = AnalyseModel(
                    id=analyse_id,
                    cv_id=uuid.UUID(item["cv_id"]),
                    job_id=uuid.UUID(job_id),
                    statut="en_cours",
                    rag_scores=item["scores_sections"],
                    rang=item["rang"],
                    batch_id=uuid.UUID(batch_id),
                    date_creation=datetime.utcnow(),
                )
                db.add(analyse)

                analyse_tasks.append({
                    "analyse_id": str(analyse_id),
                    "cv_id": item["cv_id"],
                    "cv_text": cv.texte_brut,
                    "cv_structure": cv.structure or {},
                    "rag_scores": item["scores_sections"],
                    "rag_contexts": _extract_section_texts(cv.sections),
                })

            await db.commit()

            # Exécuter les pipelines LangGraph en parallèle
            await asyncio.gather(*[
                _run_single_pipeline(
                    task["analyse_id"],
                    task["cv_id"],
                    job_id,
                    task["cv_text"],
                    task["cv_structure"],
                    job_data,
                    task["rag_scores"],
                    task["rag_contexts"],
                )
                for task in analyse_tasks
            ], return_exceptions=True)

            # Marquer le batch comme terminé
            batch.statut = "termine"
            batch.date_fin = datetime.utcnow()
            await db.commit()

            duree = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"✅ Batch terminé: {batch_id[:8]} | {duree:.1f}s")

        except Exception as e:
            logger.error(f"❌ Batch échoué {batch_id[:8]}: {e}")
            try:
                batch_result = await db.execute(
                    select(BatchAnalyseModel).where(BatchAnalyseModel.id == uuid.UUID(batch_id))
                )
                batch = batch_result.scalar_one()
                batch.statut = "erreur"
                batch.message_erreur = str(e)
                batch.date_fin = datetime.utcnow()
                await db.commit()
            except Exception:
                pass


def _extract_section_texts(sections: Optional[dict]) -> dict:
    """Extrait les textes des sections d'un CV pour le contexte LangGraph."""
    if not sections:
        return {}
    return {k: v for k, v in sections.items() if v}


async def _run_single_pipeline(
    analyse_id: str,
    cv_id: str,
    job_id: str,
    cv_text: str,
    cv_structure: dict,
    job_data: dict,
    rag_scores: dict,
    section_contexts: dict,
):
    """Exécute le pipeline LangGraph pour un seul CV."""
    from models.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        start = datetime.utcnow()
        try:
            final_state = await run_analysis(
                cv_id=cv_id,
                job_id=job_id,
                cv_text=cv_text,
                cv_structure=cv_structure,
                job_description=job_data,
                rag_scores=rag_scores,
                section_contexts=section_contexts,
            )

            rapport = final_state.get("rapport")
            score_global = rapport.get("scores", {}).get("score_global") if rapport else None
            duree = (datetime.utcnow() - start).total_seconds()

            result = await db.execute(select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id)))
            analyse = result.scalar_one()
            analyse.statut = "termine"
            analyse.rapport = rapport
            analyse.score_global = score_global
            analyse.date_fin = datetime.utcnow()
            analyse.duree_secondes = duree
            await db.commit()

            logger.info(f"✅ Pipeline CV {cv_id[:8]} | Score: {score_global:.1f} | {duree:.1f}s")

        except Exception as e:
            logger.error(f"❌ Pipeline CV {cv_id[:8]} échoué: {e}")
            try:
                result = await db.execute(select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id)))
                analyse = result.scalar_one()
                analyse.statut = "erreur"
                analyse.message_erreur = str(e)
                analyse.date_fin = datetime.utcnow()
                await db.commit()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════
# ANALYSE INDIVIDUELLE (compatibilité)
# ══════════════════════════════════════════════════════════════

@router.post("/run", response_model=AnalyseResponse, status_code=status.HTTP_202_ACCEPTED)
async def lancer_analyse(
    request: AnalyseLancerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Lance une analyse individuelle (1 CV + 1 Job)."""
    cv_result = await db.execute(select(CVModel).where(CVModel.id == request.cv_id))
    cv = cv_result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV non trouvé")

    job_result = await db.execute(select(JobModel).where(JobModel.id == request.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    analyse_id = uuid.uuid4()
    analyse = AnalyseModel(
        id=analyse_id,
        cv_id=request.cv_id,
        job_id=request.job_id,
        statut="en_cours",
        date_creation=datetime.utcnow(),
    )
    db.add(analyse)
    await db.flush()

    job_data = {
        "titre": job.titre,
        "entreprise": job.entreprise,
        "description": job.description,
        "competences_requises": job.competences_requises or [],
        "competences_souhaitees": job.competences_souhaitees or [],
        "annees_experience_min": job.annees_experience_min,
        "formation_requise": job.formation_requise,
    }

    background_tasks.add_task(
        _run_single_pipeline,
        str(analyse_id),
        str(request.cv_id),
        str(request.job_id),
        cv.texte_brut,
        cv.structure or {},
        job_data,
        {},
        _extract_section_texts(cv.sections),
    )

    return AnalyseResponse(
        id=analyse.id,
        cv_id=analyse.cv_id,
        job_id=analyse.job_id,
        statut="en_cours",
        date_creation=analyse.date_creation,
        nom_candidat=cv.structure.get("nom_complet") if cv.structure else None,
        titre_poste=job.titre,
    )


# ══════════════════════════════════════════════════════════════
# CONSULTATION
# ══════════════════════════════════════════════════════════════

@router.get("/batch/{batch_id}")
async def get_batch(batch_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère le statut et les résultats d'un batch."""
    result = await db.execute(select(BatchAnalyseModel).where(BatchAnalyseModel.id == uuid.UUID(batch_id)))
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch non trouvé")

    analyses_result = await db.execute(
        select(AnalyseModel).where(AnalyseModel.batch_id == uuid.UUID(batch_id))
        .order_by(AnalyseModel.rang)
    )
    analyses = analyses_result.scalars().all()

    top3_data = []
    for a in analyses:
        cv_r = await db.execute(select(CVModel).where(CVModel.id == a.cv_id))
        cv = cv_r.scalar_one_or_none()
        job_r = await db.execute(select(JobModel).where(JobModel.id == a.job_id))
        job = job_r.scalar_one_or_none()
        top3_data.append(_build_analyse_response(a, cv, job))

    # Enrichir le classement avec les noms des candidats
    classement = batch.classement or []
    cv_names: dict[str, str] = {}
    for item in classement:
        cid = item.get("cv_id")
        if cid and cid not in cv_names:
            cv_r = await db.execute(select(CVModel).where(CVModel.id == uuid.UUID(cid)))
            cv = cv_r.scalar_one_or_none()
            if cv:
                cv_names[cid] = cv.structure.get("nom_complet") if cv.structure else cv.nom_fichier

    rankings = [
        CandidateRanking(
            rang=item["rang"],
            cv_id=item["cv_id"],
            nom_candidat=cv_names.get(item["cv_id"]),
            score_rag_global=item["score_rag_global"],
            scores_sections=item["scores_sections"],
            analyse_id=next(
                (str(a.id) for a in analyses if str(a.cv_id) == item["cv_id"]), None
            ),
        )
        for item in classement
    ]

    return {
        "id": str(batch.id),
        "job_id": str(batch.job_id),
        "statut": batch.statut,
        "nb_cvs_soumis": len(batch.cv_ids_soumis or []),
        "classement": [r.model_dump() for r in rankings],
        "top3_analyses": [a.model_dump() for a in top3_data],
        "message_erreur": batch.message_erreur,
        "date_creation": batch.date_creation.isoformat(),
        "date_fin": batch.date_fin.isoformat() if batch.date_fin else None,
    }


@router.get("/ranking/{job_id}")
async def get_ranking(job_id: str, db: AsyncSession = Depends(get_db)):
    """Dernier classement RAG pour un poste donné."""
    result = await db.execute(
        select(BatchAnalyseModel)
        .where(BatchAnalyseModel.job_id == uuid.UUID(job_id))
        .where(BatchAnalyseModel.statut == "termine")
        .order_by(BatchAnalyseModel.date_creation.desc())
    )
    latest = result.scalars().first()
    if not latest:
        return {"classement": [], "job_id": job_id}
    return {"classement": latest.classement or [], "batch_id": str(latest.id)}


@router.get("/list/all")
async def list_analyses(db: AsyncSession = Depends(get_db)):
    """Liste toutes les analyses effectuées."""
    result = await db.execute(select(AnalyseModel).order_by(AnalyseModel.date_creation.desc()))
    analyses = result.scalars().all()

    items = []
    for a in analyses:
        cv_r = await db.execute(select(CVModel).where(CVModel.id == a.cv_id))
        cv = cv_r.scalar_one_or_none()
        job_r = await db.execute(select(JobModel).where(JobModel.id == a.job_id))
        job = job_r.scalar_one_or_none()

        nom_candidat = None
        if cv and cv.structure:
            nom_candidat = cv.structure.get("nom_complet")
        elif cv:
            nom_candidat = cv.nom_fichier

        items.append({
            "id": str(a.id),
            "cv_id": str(a.cv_id),
            "job_id": str(a.job_id),
            "statut": a.statut,
            "score_global": a.score_global,
            "recommandation": a.rapport.get("recommandation") if a.rapport else None,
            "nom_candidat": nom_candidat,
            "titre_poste": job.titre if job else None,
            "rang": a.rang,
            "date_creation": a.date_creation.isoformat(),
            "duree_secondes": a.duree_secondes,
        })

    return items


@router.get("/by-job/{job_id}")
async def list_analyses_by_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Liste toutes les analyses pour un poste donné."""
    result = await db.execute(
        select(AnalyseModel)
        .where(AnalyseModel.job_id == uuid.UUID(job_id))
        .order_by(AnalyseModel.rang.asc(), AnalyseModel.date_creation.desc())
    )
    analyses = result.scalars().all()

    items = []
    for a in analyses:
        cv_r = await db.execute(select(CVModel).where(CVModel.id == a.cv_id))
        cv = cv_r.scalar_one_or_none()
        nom_candidat = None
        if cv and cv.structure:
            nom_candidat = cv.structure.get("nom_complet")
        elif cv:
            nom_candidat = cv.nom_fichier

        items.append({
            "id": str(a.id),
            "cv_id": str(a.cv_id),
            "statut": a.statut,
            "score_global": a.score_global,
            "rang": a.rang,
            "rag_scores": a.rag_scores,
            "recommandation": a.rapport.get("recommandation") if a.rapport else None,
            "nom_candidat": nom_candidat,
            "date_creation": a.date_creation.isoformat(),
        })

    return items


@router.get("/{analyse_id}", response_model=AnalyseResponse)
async def get_analyse(analyse_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère le rapport d'une analyse."""
    result = await db.execute(select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id)))
    analyse = result.scalar_one_or_none()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")

    cv_r = await db.execute(select(CVModel).where(CVModel.id == analyse.cv_id))
    cv = cv_r.scalar_one_or_none()
    job_r = await db.execute(select(JobModel).where(JobModel.id == analyse.job_id))
    job = job_r.scalar_one_or_none()

    return _build_analyse_response(analyse, cv, job)


@router.delete("/{analyse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analyse(analyse_id: str, db: AsyncSession = Depends(get_db)):
    """Supprime une analyse."""
    result = await db.execute(select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id)))
    analyse = result.scalar_one_or_none()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    await db.delete(analyse)
    logger.info(f"🗑️  Analyse supprimée: {analyse_id[:8]}")


@router.get("/{analyse_id}/pdf")
async def get_analyse_pdf(analyse_id: str, db: AsyncSession = Depends(get_db)):
    """Génère et télécharge le rapport au format PDF."""
    from services.pdf_generator import generate_analysis_pdf
    import io

    result = await db.execute(select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id)))
    analyse = result.scalar_one_or_none()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    if analyse.statut != "termine" or not analyse.rapport:
        raise HTTPException(status_code=400, detail="L'analyse n'est pas terminée")

    cv_r = await db.execute(select(CVModel).where(CVModel.id == analyse.cv_id))
    cv = cv_r.scalar_one_or_none()
    job_r = await db.execute(select(JobModel).where(JobModel.id == analyse.job_id))
    job = job_r.scalar_one_or_none()

    cv_name = "Candidat Inconnu"
    if cv and cv.structure:
        cv_name = cv.structure.get("nom_complet", "Candidat Inconnu")
    elif cv:
        cv_name = cv.nom_fichier

    pdf_bytes = generate_analysis_pdf(
        analyse={"rapport": analyse.rapport},
        cv_name=cv_name,
        job_title=job.titre if job else "Poste Inconnu",
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapport_{analyse_id[:8]}.pdf"'},
    )
