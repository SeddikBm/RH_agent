"""
Routes Fiches de Poste — CRUD complet + indexation ChromaDB.
Le LLM parse la fiche de poste en 4 sections pour le RAG (formulaire ET drag-drop).
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import os

from models.database import JobModel, get_db
from models.schemas import JobCreate, JobResponse
from services.rag import index_job_sections, delete_job_from_chroma
from services.section_extractor import extract_job_sections
from services.parser import parse_cv
from services.llm import invoke_structured

router = APIRouter()


def _job_to_data(job: JobModel) -> dict:
    return {
        "titre": job.titre,
        "entreprise": job.entreprise,
        "description": job.description,
        "competences_requises": job.competences_requises or [],
        "competences_souhaitees": job.competences_souhaitees or [],
        "annees_experience_min": job.annees_experience_min,
        "formation_requise": job.formation_requise,
        "localisation": job.localisation,
        "type_contrat": job.type_contrat,
    }


async def _index_job_background(job_id: str, job_dict: dict) -> None:
    """Parse le job en sections via LLM et indexe dans ChromaDB (background)."""
    from models.database import AsyncSessionLocal
    from services.section_extractor import extract_job_sections
    from services.rag import index_job_sections

    async with AsyncSessionLocal() as db:
        try:
            # 1. Parser via LLM en 4 sections
            sections = await extract_job_sections(job_dict)

            # 2. Indexer dans ChromaDB
            index_job_sections(job_id, sections)

            # 3. Sauvegarder sections en base
            result = await db.execute(select(JobModel).where(JobModel.id == uuid.UUID(job_id)))
            job = result.scalar_one_or_none()
            if job:
                job.sections = sections
                await db.commit()

            logger.info(f"✅ Job indexé (background): {job_id[:8]}")
        except Exception as e:
            logger.error(f"❌ Erreur indexation background job {job_id[:8]}: {e}")


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Crée une fiche de poste depuis le formulaire.
    Le LLM parse la description en 4 sections pour le RAG (background).
    """
    job_id = uuid.uuid4()
    now = datetime.utcnow()

    job = JobModel(
        id=job_id,
        titre=job_data.titre,
        entreprise=job_data.entreprise,
        description=job_data.description,
        competences_requises=job_data.competences_requises,
        competences_souhaitees=job_data.competences_souhaitees,
        annees_experience_min=job_data.annees_experience_min,
        formation_requise=job_data.formation_requise,
        localisation=job_data.localisation,
        type_contrat=job_data.type_contrat,
        date_creation=now,
        date_modification=now,
    )
    db.add(job)
    await db.flush()

    background_tasks.add_task(
        _index_job_background,
        job_id=str(job_id),
        job_dict=_job_to_data(job),
    )

    logger.info(f"✅ Fiche de poste créée: {job_id} — {job_data.titre}")
    return JobResponse(
        id=job.id,
        date_creation=job.date_creation,
        date_modification=job.date_modification,
        **job_data.model_dump()
    )


@router.post("/extract", response_model=JobCreate)
async def extract_job(file: UploadFile = File(...)):
    """
    Extrait les données d'une fiche de poste depuis un fichier uploadé (PDF, DOCX, TXT).
    Utilise le LLM pour parser le document en champs structurés.
    """
    os.makedirs("data/uploads", exist_ok=True)
    temp_path = f"data/uploads/temp_{uuid.uuid4()}_{file.filename}"

    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        raw_text = parse_cv(temp_path)

        prompt = (
            "Tu es un expert RH. Analyse la fiche de poste suivante et extrais les informations structurées.\n"
            "Réponds en JSON conforme au schéma.\n\n"
            "Fiche de poste :\n{text}"
        )
        job_data = await invoke_structured(
            prompt_template=prompt,
            variables={"text": raw_text[:6000]},
            output_schema=JobCreate,
        )
        return job_data
    except Exception as e:
        logger.error(f"Erreur extraction fiche de poste: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/list")
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """Liste toutes les fiches de poste."""
    result = await db.execute(select(JobModel).order_by(JobModel.date_creation.desc()))
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id),
            "titre": j.titre,
            "entreprise": j.entreprise,
            "description": j.description,
            "competences_requises": j.competences_requises or [],
            "competences_souhaitees": j.competences_souhaitees or [],
            "formation_requise": j.formation_requise,
            "type_contrat": j.type_contrat,
            "localisation": j.localisation,
            "annees_experience_min": j.annees_experience_min,
            "nb_competences_requises": len(j.competences_requises or []),
            "indexe": j.sections is not None,
            "date_creation": j.date_creation.isoformat(),
        }
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère une fiche de poste par son ID."""
    result = await db.execute(select(JobModel).where(JobModel.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    return JobResponse(
        id=job.id,
        **_job_to_data(job),
        date_creation=job.date_creation,
        date_modification=job.date_modification,
    )


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Met à jour une fiche de poste et re-indexe (background)."""
    result = await db.execute(select(JobModel).where(JobModel.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    for field, value in job_data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    job.date_modification = datetime.utcnow()
    job.sections = None  # Invalider le cache des sections

    background_tasks.add_task(
        _index_job_background,
        job_id=job_id,
        job_dict=_job_to_data(job),
    )

    logger.info(f"✅ Fiche de poste mise à jour: {job_id}")
    return JobResponse(
        id=job.id,
        **_job_to_data(job),
        date_creation=job.date_creation,
        date_modification=job.date_modification,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Supprime une fiche de poste, ses analyses et son index ChromaDB."""
    from models.database import AnalyseModel, BatchAnalyseModel

    job_uuid = uuid.UUID(job_id)

    # Supprimer les analyses liées (CASCADE via FK)
    analyses_result = await db.execute(
        select(AnalyseModel).where(AnalyseModel.job_id == job_uuid)
    )
    for analyse in analyses_result.scalars().all():
        await db.delete(analyse)
    await db.flush()

    # Supprimer les batches liés
    batches_result = await db.execute(
        select(BatchAnalyseModel).where(BatchAnalyseModel.job_id == job_uuid)
    )
    for batch in batches_result.scalars().all():
        await db.delete(batch)
    await db.flush()

    result = await db.execute(select(JobModel).where(JobModel.id == job_uuid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    # Supprimer de ChromaDB
    delete_job_from_chroma(job_id)

    await db.delete(job)
    logger.info(f"🗑️  Fiche de poste supprimée: {job_id[:8]}")
