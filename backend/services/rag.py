"""
Service RAG — ChromaDB + FastEmbed (ONNX, pas de torch).
Modèle : intfloat/multilingual-e5-small (multilingue, French OK, ~380MB, rapide)

Architecture :
  - ChromaDB persisté sur disque (/app/chroma_db)
  - Embeddings ONNX locaux via fastembed (~50ms/section)
  - Collections : "cv_sections" et "job_sections"
  - Pondérations : compétences 40%, expérience 30%, formation 20%, profil 10%
"""
import threading
from typing import Optional

from loguru import logger

from config import get_settings

settings = get_settings()

# ── Pondérations officielles ──────────────────────────────────
SECTION_WEIGHTS = {
    "competences": 0.40,
    "experience":  0.30,
    "formation":   0.20,
    "profil":      0.10,
}
SECTION_NAMES = list(SECTION_WEIGHTS.keys())

# Modèle fastembed multilingue (ONNX, pas de torch)
EMBED_MODEL = settings.embed_model_name

# ── Singleton thread-safe : modèle d'embedding ───────────────
_embed_model = None
_embed_lock = threading.Lock()


def get_embed_model():
    """Charge le modèle FastEmbed une seule fois (lazy, thread-safe)."""
    global _embed_model
    if _embed_model is None:
        with _embed_lock:
            if _embed_model is None:
                from fastembed import TextEmbedding
                logger.info(f"⏳ Chargement modèle fastembed: {EMBED_MODEL}")
                _embed_model = TextEmbedding(model_name=EMBED_MODEL)
                logger.info("✅ Modèle d'embedding chargé (ONNX/fastembed)")
    return _embed_model


# ── Singleton thread-safe : ChromaDB ────────────────────────
_chroma_client = None
_chroma_lock = threading.Lock()


def get_chroma_client():
    """Retourne le client ChromaDB persisté (lazy init)."""
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                import chromadb
                logger.info(f"⏳ Init ChromaDB: {settings.chroma_persist_dir}")
                _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
                logger.info("✅ ChromaDB initialisé")
    return _chroma_client


def _get_collection(name: str):
    return get_chroma_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ── Embeddings ────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """Embedding d'un seul texte (~50ms)."""
    model = get_embed_model()
    # fastembed attend un itérable
    embeddings = list(model.embed([text[:2000]]))
    return embeddings[0].tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embeddings (plus efficace)."""
    model = get_embed_model()
    truncated = [t[:2000] for t in texts]
    embeddings = list(model.embed(truncated))
    return [e.tolist() for e in embeddings]


# ── Indexation CV ─────────────────────────────────────────────

def index_cv_sections(cv_id: str, sections: dict[str, str]) -> None:
    """Indexe les 4 sections d'un CV dans ChromaDB."""
    collection = _get_collection("cv_sections")

    # Supprimer les anciennes entrées
    try:
        existing = collection.get(where={"cv_id": str(cv_id)})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    texts, ids, metadatas = [], [], []
    for section_name in SECTION_NAMES:
        content = sections.get(section_name, "").strip()
        if not content:
            continue
        texts.append(content)
        ids.append(f"{cv_id}_{section_name}")
        metadatas.append({"cv_id": str(cv_id), "section_name": section_name})

    if not texts:
        logger.warning(f"⚠️ Aucune section pour CV {cv_id[:8]}")
        return

    embeddings = embed_texts(texts)
    collection.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)
    logger.info(f"✅ CV indexé ChromaDB: {cv_id[:8]} ({len(texts)} sections)")


# ── Indexation Job ────────────────────────────────────────────

def index_job_sections(job_id: str, sections: dict[str, str]) -> None:
    """Indexe les 4 sections d'une fiche de poste dans ChromaDB."""
    collection = _get_collection("job_sections")

    try:
        existing = collection.get(where={"job_id": str(job_id)})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    texts, ids, metadatas = [], [], []
    for section_name in SECTION_NAMES:
        content = sections.get(section_name, "").strip()
        if not content:
            continue
        texts.append(content)
        ids.append(f"job_{job_id}_{section_name}")
        metadatas.append({"job_id": str(job_id), "section_name": section_name})

    if not texts:
        logger.warning(f"⚠️ Aucune section pour job {job_id[:8]}")
        return

    embeddings = embed_texts(texts)
    collection.add(documents=texts, embeddings=embeddings, ids=ids, metadatas=metadatas)
    logger.info(f"✅ Job indexé ChromaDB: {job_id[:8]} ({len(texts)} sections)")


# ── Recherche RAG ─────────────────────────────────────────────

def search_cvs_by_section(
    job_id: str,
    cv_ids: list[str],
) -> dict[str, list[dict]]:
    """
    Pour chaque section du job, cherche les CVs les plus similaires.
    Retourne: {section_name: [{cv_id, similarity, content}]}
    """
    job_collection = _get_collection("job_sections")
    cv_collection = _get_collection("cv_sections")
    results: dict[str, list[dict]] = {}

    for section_name in SECTION_NAMES:
        job_doc_id = f"job_{job_id}_{section_name}"
        try:
            job_section = job_collection.get(
                ids=[job_doc_id],
                include=["embeddings", "documents"],
            )
        except Exception:
            results[section_name] = []
            continue

        if not job_section["ids"] or job_section.get("embeddings") is None or len(job_section.get("embeddings")) == 0:
            results[section_name] = []
            continue

        job_embedding = job_section["embeddings"][0]

        try:
            cv_str_ids = [str(cid) for cid in cv_ids]
            cv_results = cv_collection.query(
                query_embeddings=[job_embedding],
                n_results=min(len(cv_str_ids), 50),
                where={
                    "$and": [
                        {"cv_id": {"$in": cv_str_ids}},
                        {"section_name": {"$eq": section_name}},
                    ]
                },
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning(f"⚠️ Query ChromaDB '{section_name}': {e}")
            results[section_name] = []
            continue

        section_results = []
        if cv_results["ids"] and len(cv_results["ids"][0]) > 0:
            for i, _ in enumerate(cv_results["ids"][0]):
                meta = cv_results["metadatas"][0][i]
                distance = cv_results["distances"][0][i]
                similarity = max(0.0, min(1.0, 1.0 - distance))
                section_results.append({
                    "cv_id": meta["cv_id"],
                    "content": cv_results["documents"][0][i],
                    "similarity": similarity,
                })

        results[section_name] = section_results

    return results


# ── Score pondéré ─────────────────────────────────────────────

def compute_weighted_rag_scores(
    section_results: dict[str, list[dict]],
    cv_ids: list[str],
) -> list[dict]:
    """Agrège les scores par section → classement global."""
    cv_scores: dict[str, dict] = {str(cid): {"scores": {}} for cid in cv_ids}

    for section_name, results in section_results.items():
        sim_by_cv = {r["cv_id"]: r["similarity"] for r in results}
        for cid in cv_ids:
            score = round(sim_by_cv.get(str(cid), 0.0) * 100, 1)
            cv_scores[str(cid)]["scores"][section_name] = score

    ranking = []
    for cid, data in cv_scores.items():
        scores = data["scores"]
        score_global = sum(
            scores.get(s, 0) * SECTION_WEIGHTS[s] for s in SECTION_NAMES
        )
        ranking.append({
            "cv_id": cid,
            "score_rag_global": round(score_global, 1),
            "scores_sections": scores,
        })

    ranking.sort(key=lambda x: x["score_rag_global"], reverse=True)
    for i, item in enumerate(ranking):
        item["rang"] = i + 1

    return ranking


# ── Top-K ─────────────────────────────────────────────────────

def get_top_k_candidates(
    job_id: str,
    cv_ids: list[str],
    top_k: int = 3,
) -> tuple[list[dict], list[dict]]:
    """Retourne (classement_complet, top_k)."""
    section_results = search_cvs_by_section(job_id, cv_ids)
    ranking = compute_weighted_rag_scores(section_results, cv_ids)
    top = ranking[:top_k]
    logger.info(
        f"🏆 RAG | Job {job_id[:8]} | {len(ranking)} CVs | "
        f"Top3: {[r['cv_id'][:8] for r in top]}"
    )
    return ranking, top


# ── Suppression ───────────────────────────────────────────────

def delete_cv_from_chroma(cv_id: str) -> None:
    try:
        col = _get_collection("cv_sections")
        existing = col.get(where={"cv_id": str(cv_id)})
        if existing["ids"]:
            col.delete(ids=existing["ids"])
        logger.info(f"🗑️ CV supprimé ChromaDB: {cv_id[:8]}")
    except Exception as e:
        logger.warning(f"⚠️ Erreur suppression CV ChromaDB: {e}")


def delete_job_from_chroma(job_id: str) -> None:
    try:
        col = _get_collection("job_sections")
        existing = col.get(where={"job_id": str(job_id)})
        if existing["ids"]:
            col.delete(ids=existing["ids"])
        logger.info(f"🗑️ Job supprimé ChromaDB: {job_id[:8]}")
    except Exception as e:
        logger.warning(f"⚠️ Erreur suppression Job ChromaDB: {e}")
