"""Routes Analyses — Lancement, consultation et export de rapports."""
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import AnalyseModel, CVModel, JobModel, get_db
from models.schemas import AnalyseLancerRequest, AnalyseListItem, AnalyseResponse
from agents.graph import run_analysis

router = APIRouter()


# ── Lancer une analyse ────────────────────────────────────

@router.post("/run", response_model=AnalyseResponse, status_code=status.HTTP_202_ACCEPTED)
async def lancer_analyse(
    request: AnalyseLancerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Lance une analyse d'un CV contre une fiche de poste.
    L'analyse s'exécute en arrière-plan (BackgroundTask).
    Retourne immédiatement avec le statut 'en_attente'.
    """
    # Vérifier que le CV existe
    cv_result = await db.execute(select(CVModel).where(CVModel.id == request.cv_id))
    cv = cv_result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV non trouvé")

    # Vérifier que la fiche de poste existe
    job_result = await db.execute(select(JobModel).where(JobModel.id == request.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    # Créer l'enregistrement de l'analyse
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

    logger.info(f"🚀 Analyse lancée: {analyse_id} | CV: {request.cv_id} | Job: {request.job_id}")

    # Préparer les données du job pour le pipeline
    job_data = {
        "titre": job.titre,
        "entreprise": job.entreprise,
        "description": job.description,
        "competences_requises": job.competences_requises or [],
        "competences_souhaitees": job.competences_souhaitees or [],
        "annees_experience_min": job.annees_experience_min,
        "formation_requise": job.formation_requise,
    }

    # Lancer le pipeline en arrière-plan
    background_tasks.add_task(
        _execute_analysis,
        analyse_id=str(analyse_id),
        cv_id=str(request.cv_id),
        job_id=str(request.job_id),
        cv_text=cv.texte_brut,
        job_data=job_data,
        nom_candidat=cv.structure.get("nom_complet") if cv.structure else None,
        titre_poste=job.titre,
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


async def _execute_analysis(
    analyse_id: str,
    cv_id: str,
    job_id: str,
    cv_text: str,
    job_data: dict,
    nom_candidat: str = None,
    titre_poste: str = None,
):
    """Exécute le pipeline LangGraph en arrière-plan et met à jour la BDD."""
    from models.database import AsyncSessionLocal
    
    start_time = datetime.utcnow()

    async with AsyncSessionLocal() as db:
        try:
            # Exécuter le pipeline
            final_state = await run_analysis(
                cv_id=cv_id,
                job_id=job_id,
                cv_text=cv_text,
                job_description=job_data,
            )

            rapport = final_state.get("rapport")
            score_global = rapport.get("scores", {}).get("score_global") if rapport else None
            duree = (datetime.utcnow() - start_time).total_seconds()

            # Mettre à jour l'analyse en base
            result = await db.execute(
                select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id))
            )
            analyse = result.scalar_one()
            analyse.statut = "termine"
            analyse.rapport = rapport
            analyse.score_global = score_global
            analyse.date_fin = datetime.utcnow()
            analyse.duree_secondes = duree

            await db.commit()
            logger.info(
                f"✅ Analyse terminée: {analyse_id} | Score: {score_global:.1f} | "
                f"Durée: {duree:.1f}s"
            )

        except Exception as e:
            logger.error(f"❌ Analyse échouée {analyse_id}: {e}")
            try:
                result = await db.execute(
                    select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id))
                )
                analyse = result.scalar_one()
                analyse.statut = "erreur"
                analyse.message_erreur = str(e)
                analyse.date_fin = datetime.utcnow()
                await db.commit()
            except Exception as db_err:
                logger.error(f"❌ Échec mise à jour statut erreur: {db_err}")


# ── Consulter une analyse ─────────────────────────────────

@router.get("/{analyse_id}", response_model=AnalyseResponse)
async def get_analyse(analyse_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère le rapport d'une analyse par son ID."""
    result = await db.execute(
        select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id))
    )
    analyse = result.scalar_one_or_none()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")

    # Récupérer les noms pour l'affichage
    cv_result = await db.execute(select(CVModel).where(CVModel.id == analyse.cv_id))
    cv = cv_result.scalar_one_or_none()
    job_result = await db.execute(select(JobModel).where(JobModel.id == analyse.job_id))
    job = job_result.scalar_one_or_none()

    nom_candidat = None
    if cv and cv.structure:
        nom_candidat = cv.structure.get("nom_complet")

    from models.schemas import RapportAnalyse, ScoresCategorie, CorrespondanceCompetence, NiveauMatch
    rapport_obj = None
    if analyse.rapport:
        r = analyse.rapport
        scores = r.get("scores", {})
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
            disclaimer=r.get("disclaimer", ""),
        )

    return AnalyseResponse(
        id=analyse.id,
        cv_id=analyse.cv_id,
        job_id=analyse.job_id,
        statut=analyse.statut,
        rapport=rapport_obj,
        message_erreur=analyse.message_erreur,
        date_creation=analyse.date_creation,
        date_fin=analyse.date_fin,
        duree_secondes=analyse.duree_secondes,
        nom_candidat=nom_candidat,
        titre_poste=job.titre if job else None,
    )


@router.get("/list/all")
async def list_analyses(db: AsyncSession = Depends(get_db)):
    """Liste toutes les analyses effectuées."""
    result = await db.execute(select(AnalyseModel).order_by(AnalyseModel.date_creation.desc()))
    analyses = result.scalars().all()

    items = []
    for a in analyses:
        cv_result = await db.execute(select(CVModel).where(CVModel.id == a.cv_id))
        cv = cv_result.scalar_one_or_none()
        job_result = await db.execute(select(JobModel).where(JobModel.id == a.job_id))
        job = job_result.scalar_one_or_none()

        recommandation = None
        if a.rapport:
            recommandation = a.rapport.get("recommandation")

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
            "recommandation": recommandation,
            "nom_candidat": nom_candidat,
            "titre_poste": job.titre if job else None,
            "date_creation": a.date_creation.isoformat(),
            "duree_secondes": a.duree_secondes,
        })

    return items


@router.delete("/{analyse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analyse(analyse_id: str, db: AsyncSession = Depends(get_db)):
    """Supprime une analyse."""
    result = await db.execute(
        select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id))
    )
    analyse = result.scalar_one_or_none()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    await db.delete(analyse)
    logger.info(f"🗑️  Analyse supprimée: {analyse_id}")

@router.get("/{analyse_id}/pdf")
async def get_analyse_pdf(analyse_id: str, db: AsyncSession = Depends(get_db)):
    """Génère et télécharge le rapport d'analyse au format PDF."""
    from services.pdf_generator import generate_analysis_pdf
    import io

    result = await db.execute(
        select(AnalyseModel).where(AnalyseModel.id == uuid.UUID(analyse_id))
    )
    analyse = result.scalar_one_or_none()
    if not analyse:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
        
    if analyse.statut != "termine" or not analyse.rapport:
        raise HTTPException(status_code=400, detail="L'analyse n'est pas terminée ou ne contient pas de rapport")

    # Récupérer les noms
    cv_result = await db.execute(select(CVModel).where(CVModel.id == analyse.cv_id))
    cv = cv_result.scalar_one_or_none()
    job_result = await db.execute(select(JobModel).where(JobModel.id == analyse.job_id))
    job = job_result.scalar_one_or_none()

    cv_name = "Candidat Inconnu"
    if cv and cv.structure:
        cv_name = cv.structure.get("nom_complet", "Candidat Inconnu")
    elif cv:
        cv_name = cv.nom_fichier

    job_title = job.titre if job else "Poste Inconnu"

    # Générer le PDF
    pdf_bytes = generate_analysis_pdf(
        analyse={"rapport": analyse.rapport},
        cv_name=cv_name,
        job_title=job_title
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rapport_{analyse_id}.pdf"'}
    )
