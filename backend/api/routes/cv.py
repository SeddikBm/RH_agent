"""
Routes CV — Upload, parsing par sections via LLM, indexation ChromaDB.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.database import CVModel, get_db
from models.schemas import CVResponse, CVStructure
from services.parser import parse_cv
from services.section_extractor import extract_cv_sections
from services.rag import index_cv_sections, delete_cv_from_chroma

router = APIRouter()
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
}


async def _index_cv_background(cv_id: str, texte_brut: str) -> None:
    """Parse les sections du CV via LLM et indexe dans ChromaDB (background)."""
    from models.database import AsyncSessionLocal
    from services.section_extractor import extract_cv_sections
    from services.rag import index_cv_sections

    async with AsyncSessionLocal() as db:
        try:
            # 1. Parser le CV en 4 sections via LLM
            sections = await extract_cv_sections(texte_brut)

            # 2. Indexer dans ChromaDB (synchrone, rapide)
            index_cv_sections(cv_id, sections)

            # 3. Sauvegarder les sections en base pour réutilisation
            result = await db.execute(select(CVModel).where(CVModel.id == uuid.UUID(cv_id)))
            cv = result.scalar_one_or_none()
            if cv:
                cv.sections = sections
                await db.commit()

            logger.info(f"✅ CV indexé (background): {cv_id[:8]}")
        except Exception as e:
            logger.error(f"❌ Erreur indexation background CV {cv_id[:8]}: {e}")


@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload un CV (PDF, DOCX, TXT).
    1. Extrait le texte brut
    2. Sauvegarde en base (immédiat)
    3. Parse en 4 sections + indexe ChromaDB (background)
    """
    # ── Validation du type de fichier ───────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Format non supporté: {file.content_type}. Utilisez PDF, DOCX ou TXT.",
        )

    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux. Maximum: {settings.max_file_size_mb}MB",
        )

    # ── Sauvegarde du fichier ────────────────────────────────
    cv_id = uuid.uuid4()
    ext = ALLOWED_TYPES[file.content_type]
    safe_filename = f"{cv_id}{ext}"
    file_path = os.path.join(settings.upload_dir, safe_filename)

    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(contents)

    # ── Parsing du texte brut ────────────────────────────────
    try:
        texte_brut = parse_cv(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Impossible de lire le fichier: {str(e)}",
        )

    if len(texte_brut.strip()) < 50:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier CV semble vide ou illisible.",
        )

    # ── Enregistrement en base ───────────────────────────────
    cv_record = CVModel(
        id=cv_id,
        nom_fichier=file.filename or safe_filename,
        chemin_fichier=file_path,
        texte_brut=texte_brut,
        taille_fichier=len(contents),
        date_upload=datetime.utcnow(),
    )
    db.add(cv_record)
    await db.flush()

    # ── Indexation en background (LLM parsing + ChromaDB) ───
    background_tasks.add_task(_index_cv_background, str(cv_id), texte_brut)

    logger.info(f"✅ CV enregistré + indexation lancée: {cv_id}")
    return CVResponse(
        id=cv_record.id,
        nom_fichier=cv_record.nom_fichier,
        chemin_fichier=cv_record.chemin_fichier,
        texte_brut=texte_brut[:500] + "..." if len(texte_brut) > 500 else texte_brut,
        date_upload=cv_record.date_upload,
        taille_fichier=cv_record.taille_fichier,
    )


@router.get("/list")
async def list_cvs(db: AsyncSession = Depends(get_db)):
    """Liste tous les CVs uploadés."""
    result = await db.execute(select(CVModel).order_by(CVModel.date_upload.desc()))
    cvs = result.scalars().all()
    return [
        {
            "id": str(cv.id),
            "nom_fichier": cv.nom_fichier,
            "nom_candidat": cv.structure.get("nom_complet") if cv.structure else None,
            "taille_fichier": cv.taille_fichier,
            "date_upload": cv.date_upload.isoformat(),
            "indexe": cv.sections is not None,
        }
        for cv in cvs
    ]


@router.get("/{cv_id}", response_model=CVResponse)
async def get_cv(cv_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère les données d'un CV par son ID."""
    result = await db.execute(select(CVModel).where(CVModel.id == uuid.UUID(cv_id)))
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV non trouvé")

    return CVResponse(
        id=cv.id,
        nom_fichier=cv.nom_fichier,
        chemin_fichier=cv.chemin_fichier,
        texte_brut=cv.texte_brut[:500] + "..." if len(cv.texte_brut) > 500 else cv.texte_brut,
        structure=CVStructure(**cv.structure) if cv.structure else None,
        date_upload=cv.date_upload,
        taille_fichier=cv.taille_fichier,
    )


@router.delete("/{cv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cv(cv_id: str, db: AsyncSession = Depends(get_db)):
    """Supprime un CV (fichier physique, base de données et index ChromaDB)."""
    result = await db.execute(select(CVModel).where(CVModel.id == uuid.UUID(cv_id)))
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV non trouvé")

    # Supprimer le fichier physique
    if os.path.exists(cv.chemin_fichier):
        try:
            os.remove(cv.chemin_fichier)
        except Exception:
            pass

    # Supprimer de ChromaDB
    delete_cv_from_chroma(cv_id)

    await db.delete(cv)
    logger.info(f"🗑️  CV supprimé: {cv_id[:8]}")
