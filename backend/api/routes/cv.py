"""Routes CV — Upload, parsing, indexation."""
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models.database import CVModel, get_db
from models.schemas import CVResponse, CVStructure
from services.parser import parse_cv
from services.rag import index_cv, delete_cv_from_index

router = APIRouter()
settings = get_settings()

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
}


@router.post("/upload", response_model=CVResponse, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload un CV (PDF, DOCX, TXT), le parse et l'indexe dans ChromaDB.
    """
    # ── Validation du type de fichier ──────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Format non supporté: {file.content_type}. Utilisez PDF, DOCX ou TXT.",
        )

    # ── Validation de la taille ────────────────────────────
    contents = await file.read()
    if len(contents) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux. Maximum: {settings.max_file_size_mb}MB",
        )

    # ── Sauvegarde du fichier ──────────────────────────────
    cv_id = uuid.uuid4()
    ext = ALLOWED_TYPES[file.content_type]
    safe_filename = f"{cv_id}{ext}"
    file_path = os.path.join(settings.upload_dir, safe_filename)

    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(contents)

    logger.info(f"📁 CV sauvegardé: {file_path}")

    # ── Parsing du texte ───────────────────────────────────
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

    # ── Enregistrement en base ─────────────────────────────
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

    # ── Indexation RAG (asynchrone, best effort) ───────────
    try:
        await index_cv(
            cv_id=cv_id,
            text=texte_brut,
            metadata={
                "nom_fichier": file.filename or safe_filename,
                "date_upload": datetime.utcnow().isoformat(),
                "taille": len(contents),
            },
        )
    except Exception as e:
        logger.warning(f"⚠️ Indexation RAG échouée (non bloquant): {e}")

    logger.info(f"✅ CV enregistré: {cv_id}")
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
            "taille_fichier": cv.taille_fichier,
            "date_upload": cv.date_upload.isoformat(),
            "a_structure": cv.structure is not None,
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
    """Supprime un CV (fichier, base de données et index ChromaDB)."""
    result = await db.execute(select(CVModel).where(CVModel.id == uuid.UUID(cv_id)))
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV non trouvé")

    # Supprimer le fichier physique
    if os.path.exists(cv.chemin_fichier):
        os.remove(cv.chemin_fichier)

    # Supprimer de ChromaDB
    try:
        delete_cv_from_index(uuid.UUID(cv_id))
    except Exception as e:
        logger.warning(f"⚠️ Suppression RAG échouée: {e}")

    await db.delete(cv)
    logger.info(f"🗑️  CV supprimé: {cv_id}")
