"""
Service RAG — ChromaDB + Ollama (mxbai-embed-large).
Indexation et recherche sémantique de CVs et fiches de poste.
"""
import asyncio
from typing import Optional
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings
import httpx
from loguru import logger

from config import get_settings

settings = get_settings()


# ── Singleton ChromaDB ─────────────────────────────────────
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection_cv: Optional[chromadb.Collection] = None
_collection_job: Optional[chromadb.Collection] = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"✅ ChromaDB initialisé : {settings.chroma_persist_dir}")
    return _chroma_client


def get_collection(name: str) -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ── Embeddings via Ollama ──────────────────────────────────

async def get_embedding(text: str) -> list[float]:
    """
    Génère un embedding via Ollama (mxbai-embed-large) en local.
    Retourne un vecteur de 1024 dimensions.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={
                "model": settings.ollama_embed_model,
                "prompt": text,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Génère des embeddings en batch (concurrent)."""
    tasks = [get_embedding(text) for text in texts]
    return await asyncio.gather(*tasks)


def _truncate_text(text: str, max_chars: int = 8000) -> str:
    """Tronque le texte pour éviter des embeddings trop longs."""
    return text[:max_chars] if len(text) > max_chars else text


# ── Indexation ─────────────────────────────────────────────

async def index_cv(cv_id: UUID, text: str, metadata: dict) -> None:
    """Indexe un CV dans ChromaDB avec son embedding Ollama."""
    collection = get_collection("cvs")

    truncated = _truncate_text(text)
    embedding = await get_embedding(truncated)

    doc_id = str(cv_id)
    safe_metadata = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                     for k, v in metadata.items()}

    # Upsert (remplace si déjà existant)
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[truncated],
        metadatas=[safe_metadata],
    )
    logger.info(f"✅ CV indexé dans ChromaDB: {doc_id}")


async def index_job(job_id: UUID, text: str, metadata: dict) -> None:
    """Indexe une fiche de poste dans ChromaDB."""
    collection = get_collection("jobs")

    truncated = _truncate_text(text)
    embedding = await get_embedding(truncated)

    doc_id = str(job_id)
    safe_metadata = {k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                     for k, v in metadata.items()}

    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[truncated],
        metadatas=[safe_metadata],
    )
    logger.info(f"✅ Fiche de poste indexée: {doc_id}")


# ── Recherche sémantique ───────────────────────────────────

async def search_cv_against_job(job_text: str, top_k: int = 3) -> list[dict]:
    """
    Recherche les CVs les plus similaires à une fiche de poste.
    Retourne les top_k résultats avec scores de similarité.
    """
    collection = get_collection("cvs")
    embedding = await get_embedding(_truncate_text(job_text))

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    items = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            similarity = 1 - results["distances"][0][i]  # cosine: distance → similarity
            items.append({
                "cv_id": doc_id,
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "similarity": round(similarity, 4),
            })

    return items


async def search_job_for_cv(cv_text: str, top_k: int = 3) -> list[dict]:
    """
    Recherche les fiches de poste les plus similaires à un CV.
    """
    collection = get_collection("jobs")
    if collection.count() == 0:
        return []

    embedding = await get_embedding(_truncate_text(cv_text))

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    items = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            similarity = 1 - results["distances"][0][i]
            items.append({
                "job_id": doc_id,
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "similarity": round(similarity, 4),
            })

    return items


async def get_relevant_context(query: str, collection_name: str, top_k: int = 5) -> list[str]:
    """
    Recherche générique dans une collection ChromaDB.
    Retourne les textes les plus pertinents pour une requête.
    """
    collection = get_collection(collection_name)
    if collection.count() == 0:
        return []

    embedding = await get_embedding(query)

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, collection.count()),
        include=["documents"],
    )

    if results["documents"] and results["documents"][0]:
        return results["documents"][0]

    return []


# ── Suppression ────────────────────────────────────────────

def delete_cv_from_index(cv_id: UUID) -> None:
    collection = get_collection("cvs")
    collection.delete(ids=[str(cv_id)])
    logger.info(f"🗑️  CV supprimé de ChromaDB: {cv_id}")


def delete_job_from_index(job_id: UUID) -> None:
    collection = get_collection("jobs")
    collection.delete(ids=[str(job_id)])
    logger.info(f"🗑️  Fiche supprimée de ChromaDB: {job_id}")
