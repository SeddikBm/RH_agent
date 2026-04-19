"""Routes Fiches de Poste — CRUD complet."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import os

from models.database import JobModel, get_db
from models.schemas import JobCreate, JobResponse
from services.rag import index_job, delete_job_from_index
from services.parser import parse_cv
from services.llm import invoke_structured

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_data: JobCreate, db: AsyncSession = Depends(get_db)):
    """Crée une nouvelle fiche de poste."""
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

    # Indexer dans ChromaDB
    job_text = f"{job_data.titre}\n{job_data.description}\n{' '.join(job_data.competences_requises)}"
    try:
        await index_job(
            job_id=job_id,
            text=job_text,
            metadata={
                "titre": job_data.titre,
                "entreprise": job_data.entreprise or "",
                "type_contrat": job_data.type_contrat or "",
            },
        )
    except Exception as e:
        logger.warning(f"⚠️ Indexation job RAG échouée: {e}")

    logger.info(f"✅ Fiche de poste créée: {job_id} — {job_data.titre}")
    return JobResponse(id=job.id, date_creation=job.date_creation, date_modification=job.date_modification, **job_data.model_dump())


@router.post("/extract", response_model=JobCreate)
async def extract_job(file: UploadFile = File(...)):
    """Extrait les données d'une fiche de poste depuis un fichier (PDF, DOCX, TXT)."""
    # Sauvegarder temp
    os.makedirs("data/uploads", exist_ok=True)
    temp_path = f"data/uploads/temp_{uuid.uuid4()}_{file.filename}"
    
    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())
            
        # Extraire le texte
        raw_text = parse_cv(temp_path)
        
        # Invoquer LLM pour structurer
        prompt = (
            "Analyse le document suivant (qui est une fiche de poste) et extrais les informations requises.\n"
            "Document:\n"
            "{text}"
        )
        job_data = await invoke_structured(prompt_template=prompt, variables={"text": raw_text}, output_schema=JobCreate)
        return job_data
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction de la fiche de poste: {e}")
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
        titre=job.titre,
        entreprise=job.entreprise,
        description=job.description,
        competences_requises=job.competences_requises or [],
        competences_souhaitees=job.competences_souhaitees or [],
        annees_experience_min=job.annees_experience_min,
        formation_requise=job.formation_requise,
        localisation=job.localisation,
        type_contrat=job.type_contrat,
        date_creation=job.date_creation,
        date_modification=job.date_modification,
    )


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id: str, job_data: JobCreate, db: AsyncSession = Depends(get_db)):
    """Met à jour une fiche de poste."""
    result = await db.execute(select(JobModel).where(JobModel.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    for field, value in job_data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    job.date_modification = datetime.utcnow()

    logger.info(f"✅ Fiche de poste mise à jour: {job_id}")
    return JobResponse(
        id=job.id,
        titre=job.titre,
        entreprise=job.entreprise,
        description=job.description,
        competences_requises=job.competences_requises or [],
        competences_souhaitees=job.competences_souhaitees or [],
        annees_experience_min=job.annees_experience_min,
        formation_requise=job.formation_requise,
        localisation=job.localisation,
        type_contrat=job.type_contrat,
        date_creation=job.date_creation,
        date_modification=job.date_modification,
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Supprime une fiche de poste."""
    # Suppression en cascade manuelle via ORM pour éviter IntegrityError
    from models.database import AnalyseModel
    analyses_result = await db.execute(select(AnalyseModel).where(AnalyseModel.job_id == uuid.UUID(job_id)))
    analyses = analyses_result.scalars().all()
    for analyse in analyses:
        await db.delete(analyse)
    await db.flush()

    result = await db.execute(select(JobModel).where(JobModel.id == uuid.UUID(job_id)))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Fiche de poste non trouvée")

    try:
        delete_job_from_index(uuid.UUID(job_id))
    except Exception as e:
        logger.warning(f"⚠️ Suppression RAG job échouée: {e}")

    await db.delete(job)
    logger.info(f"🗑️  Fiche de poste supprimée: {job_id}")
