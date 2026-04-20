"""
FastAPI — Point d'entrée principal de l'application.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from config import get_settings
from models.database import create_tables
from api.routes import cv, job, analysis

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle : initialisation au démarrage."""
    logger.info("🚀 Démarrage de l'Agent RH...")

    # Créer les répertoires nécessaires
    os.makedirs(settings.upload_dir, exist_ok=True)

    # Initialiser les tables PostgreSQL
    await create_tables()
    logger.info("✅ Base de données initialisée")

    # Configurer LangSmith si activé
    if settings.langchain_tracing_v2.lower() == "true":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
        logger.info(f"🔭 LangSmith activé → projet: {settings.langsmith_project}")

    logger.info("✅ Agent RH prêt sur http://0.0.0.0:8000")
    yield

    logger.info("🛑 Arrêt de l'Agent RH")


# ── Application FastAPI ────────────────────────────────────
app = FastAPI(
    title="Agent d'Évaluation de Candidatures RH",
    description=(
        "API d'analyse de CVs et de matching avec des fiches de poste. "
        "Propulsé par LangGraph, GroqCloud et PGVector (embeddings par section). "
        "Outil d'aide à la décision — ne remplace pas le jugement humain."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────
app.include_router(cv.router, prefix="/api/cv", tags=["CVs"])
app.include_router(job.router, prefix="/api/jobs", tags=["Fiches de Poste"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analyses"])


# ── Health Check ──────────────────────────────────────────
@app.get("/health", tags=["Santé"])
async def health_check():
    return {
        "status": "ok",
        "service": "Agent RH d'Évaluation de Candidatures",
        "version": "1.0.0",
    }
