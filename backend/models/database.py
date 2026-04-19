"""
Base de données SQLAlchemy asynchrone — PostgreSQL.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON, Column, DateTime, Float, Integer, String, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import get_settings

settings = get_settings()

# ── Engine asynchrone ──────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ── Base déclarative ───────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Modèles ORM ────────────────────────────────────────────

class CVModel(Base):
    __tablename__ = "cvs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nom_fichier = Column(String(255), nullable=False)
    chemin_fichier = Column(String(500), nullable=False)
    texte_brut = Column(Text, nullable=False)
    structure = Column(JSON, nullable=True)        # CVStructure sérialisé
    taille_fichier = Column(Integer, nullable=False)
    date_upload = Column(DateTime, default=datetime.utcnow, nullable=False)


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titre = Column(String(200), nullable=False)
    entreprise = Column(String(200), nullable=True)
    description = Column(Text, nullable=False)
    competences_requises = Column(JSON, default=list)
    competences_souhaitees = Column(JSON, default=list)
    annees_experience_min = Column(Integer, nullable=True)
    formation_requise = Column(String(500), nullable=True)
    localisation = Column(String(200), nullable=True)
    type_contrat = Column(String(100), nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_modification = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AnalyseModel(Base):
    __tablename__ = "analyses"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cv_id = Column(PG_UUID(as_uuid=True), ForeignKey("cvs.id"), nullable=False)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    statut = Column(String(50), default="en_attente", nullable=False)
    rapport = Column(JSON, nullable=True)          # RapportAnalyse sérialisé
    message_erreur = Column(Text, nullable=True)
    score_global = Column(Float, nullable=True)
    date_creation = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_fin = Column(DateTime, nullable=True)
    duree_secondes = Column(Float, nullable=True)


# ── Init tables ────────────────────────────────────────────
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Dépendance session ─────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
