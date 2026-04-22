<p align="center">
  <img src="docs/images/dashboard_preview.png" alt="RH Agent Dashboard" width="800"/>
</p>

<h1 align="center">🤖 RH Agent — AI-Powered Recruitment Assistant</h1>

<p align="center">
  <em>Intelligent CV analysis & candidate ranking powered by LangGraph, RAG, and LLM</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React"/>
  <img src="https://img.shields.io/badge/LangGraph-0.2-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Documentation](#-api-documentation)
- [Pipeline Details](#-pipeline-details)
- [Screenshots](#-screenshots)
- [License](#-license)

---

## 🎯 Overview

**RH Agent** is a full-stack AI-powered recruitment assistant that automates CV analysis and candidate evaluation against job descriptions. It combines **semantic search (RAG)** with **multi-agent LLM analysis (LangGraph)** to provide recruiters with intelligent, explainable, and bias-aware candidate assessments.

The system is designed as a **decision-support tool** — it assists recruiters at every step while keeping the human in the loop for final decisions.

### Key Principles

- 🔍 **Structure before comparison** — CVs and job posts are parsed into normalized sections before matching
- 📊 **Filter before deep analysis** — RAG pre-ranking on all candidates, then LLM deep-dive on shortlisted profiles
- ⚖️ **Hybrid scoring** — Combines semantic similarity (RAG) with qualitative LLM evaluation
- 👤 **Human-in-the-loop** — Recruiters select which candidates proceed to detailed analysis
- 🛡️ **Ethical guardrails** — Bias detection, score validation, and mandatory disclaimers

---

## 🏗 Architecture

<p align="center">
  <img src="docs/images/architecture.png" alt="Architecture Diagram" width="800"/>
</p>

The application is composed of four main blocks:

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | React 18 + Vite | Interactive UI for recruiters |
| **Backend** | FastAPI + LangGraph | API, orchestration & AI pipeline |
| **Relational DB** | PostgreSQL 16 | CVs, jobs, analyses, reports |
| **Vector Store** | ChromaDB + FastEmbed | Semantic search & embeddings |

---

## ✨ Features

### 📄 Job Post Management
- Create job descriptions manually or by uploading PDF/DOCX/TXT files
- LLM-powered automatic extraction of structured job requirements
- Section-based indexing for semantic matching

### 📤 CV Processing
- Drag & drop multi-file upload (PDF, DOCX, TXT)
- Automatic text extraction and semantic sectioning
- Background indexing into ChromaDB vector store

### 🔍 RAG Pre-Ranking
- Section-by-section semantic similarity scoring
- Weighted ranking: **Competences 40%** · **Experience 30%** · **Education 20%** · **Profile 10%**
- Fast filtering across large candidate pools

### 🧠 LangGraph Deep Analysis
- Multi-node pipeline: **Extract Skills → Match Job → Score → Report**
- Hybrid scoring: **70% LLM** + **30% RAG**
- Structured report with strengths, weaknesses, and recommendations

### 🛡️ Ethical Guardrails
- Mandatory disclaimer on all reports
- Score coherence validation
- Bias keyword detection
- Recommendation consistency enforcement (≥70: Interview · 50-69: Consider · <50: Insufficient)

### 📊 PDF Report Generation
- Professional PDF export with ReportLab
- Multi-criteria breakdown with visual scoring
- Exportable for archiving and sharing

---

## 🛠 Tech Stack

### Backend
| Package | Purpose |
|---------|---------|
| `FastAPI` + `Uvicorn` | Async REST API server |
| `SQLAlchemy` + `asyncpg` | Async PostgreSQL ORM |
| `LangGraph` + `LangChain` | Multi-agent AI pipeline |
| `OpenAI` (`gpt-4o-mini`) | LLM for analysis & generation |
| `ChromaDB` + `FastEmbed` | Vector store & local embeddings |
| `PyMuPDF` + `python-docx` | Document parsing (PDF, DOCX) |
| `ReportLab` | PDF report generation |
| `Pydantic` | Data validation & schemas |
| `Loguru` | Structured logging |
| `Tenacity` | Retry logic for LLM calls |

### Frontend
| Package | Purpose |
|---------|---------|
| `React 18` + `Vite` | SPA framework & build tool |
| `react-router-dom` | Client-side routing |
| `Recharts` | Data visualization & charts |
| `react-dropzone` | File upload interface |
| `react-hot-toast` | Toast notifications |
| `Lucide React` | Icon library |

### Infrastructure
| Tool | Purpose |
|------|---------|
| `Docker` + `Docker Compose` | Containerized deployment |
| `PostgreSQL 16` | Relational database |
| `Nginx` | Frontend static serving & reverse proxy |
| `LangSmith` | LLM observability & tracing |

---

## 📁 Project Structure

```
RH_agent/
├── 📂 backend/
│   ├── 📂 agents/
│   │   ├── graph.py              # LangGraph pipeline definition
│   │   ├── state.py              # Agent state schema
│   │   └── 📂 nodes/
│   │       ├── extract_skills.py # Node 1: Skill extraction
│   │       ├── match_job.py      # Node 2: CV ↔ Job matching
│   │       ├── score.py          # Node 3: Multi-criteria scoring
│   │       └── report.py         # Node 4: Report generation
│   ├── 📂 api/routes/
│   │   ├── cv.py                 # CV upload & management endpoints
│   │   ├── job.py                # Job post CRUD endpoints
│   │   └── analysis.py           # Analysis orchestration endpoints
│   ├── 📂 guardrails/
│   │   └── validators.py         # Ethical & structural validators
│   ├── 📂 models/
│   │   ├── database.py           # SQLAlchemy models & DB setup
│   │   └── schemas.py            # Pydantic request/response schemas
│   ├── 📂 services/
│   │   ├── llm.py                # LLM client configuration
│   │   ├── parser.py             # Document text extraction
│   │   ├── rag.py                # RAG engine & ChromaDB operations
│   │   ├── section_extractor.py  # Semantic section parsing
│   │   └── pdf_generator.py      # PDF report builder
│   ├── config.py                 # App settings & env loading
│   ├── main.py                   # FastAPI entry point
│   ├── requirements.txt
│   └── Dockerfile
│
├── 📂 frontend/
│   ├── 📂 src/
│   │   ├── 📂 pages/
│   │   │   ├── Dashboard.jsx     # Overview & statistics
│   │   │   ├── Jobs.jsx          # Job post management
│   │   │   ├── Upload.jsx        # CV upload & batch analysis
│   │   │   ├── Analyses.jsx      # Analysis tracking
│   │   │   └── Report.jsx        # Detailed report view
│   │   ├── 📂 components/
│   │   │   └── Layout.jsx        # App shell & navigation
│   │   ├── 📂 api/               # API client utilities
│   │   ├── App.jsx               # Router & app root
│   │   ├── main.jsx              # React entry point
│   │   └── index.css             # Global styles
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── Dockerfile
│
├── 📂 data/                      # Uploaded files & ChromaDB data
├── 📂 outputs/                   # Generated PDF reports
├── docker-compose.yml
├── .env                          # Environment configuration
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) & Docker Compose
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone the repository

```bash
git clone https://github.com/SeddikBm/RH_agent.git
cd RH_agent
```

### 2. Configure environment

Copy the `.env.example` or create a `.env` file at the project root:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Embeddings (local, no external API needed)
EMBED_MODEL_NAME=BAAI/bge-small-en-v1.5

# ChromaDB
CHROMA_PERSIST_DIR=/app/chroma_db

# PostgreSQL
POSTGRES_USER=hr_agent
POSTGRES_PASSWORD=hr_agent_pass
POSTGRES_DB=hr_agent_db
DATABASE_URL=postgresql+asyncpg://hr_agent:hr_agent_pass@localhost:5432/hr_agent_db

# LangSmith (optional — for tracing)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_PROJECT=hr-agent-evaluateur

# File uploads
UPLOAD_DIR=/app/data/uploads
MAX_FILE_SIZE_MB=10

# Security
SECRET_KEY=change_this_to_a_random_secret_key_min_32_chars
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 3. Launch with Docker Compose

```bash
docker-compose up --build
```

This will start three services:

| Service | URL |
|---------|-----|
| 🖥️ **Frontend** | [http://localhost:3000](http://localhost:3000) |
| ⚙️ **Backend API** | [http://localhost:8000](http://localhost:8000) |
| 📖 **API Docs (Swagger)** | [http://localhost:8000/api/docs](http://localhost:8000/api/docs) |
| 🗄️ **PostgreSQL** | `localhost:5432` |

### 4. Start recruiting! 🎉

1. Create a job post (manually or upload a document)
2. Upload candidate CVs
3. Launch batch analysis
4. Review RAG pre-ranking
5. Select top candidates for deep analysis
6. View detailed reports & export PDF

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for LLM calls |
| `OPENAI_MODEL` | ❌ | Model name (default: `gpt-4o-mini`) |
| `EMBED_MODEL_NAME` | ❌ | FastEmbed model (default: `BAAI/bge-small-en-v1.5`) |
| `POSTGRES_USER` | ❌ | PostgreSQL user (default: `hr_agent`) |
| `POSTGRES_PASSWORD` | ❌ | PostgreSQL password (default: `hr_agent_pass`) |
| `POSTGRES_DB` | ❌ | Database name (default: `hr_agent_db`) |
| `DATABASE_URL` | ❌ | Full connection string |
| `CHROMA_PERSIST_DIR` | ❌ | ChromaDB persistence path |
| `LANGSMITH_TRACING` | ❌ | Enable LangSmith tracing |
| `LANGSMITH_API_KEY` | ❌ | LangSmith API key |
| `UPLOAD_DIR` | ❌ | Upload directory path |
| `MAX_FILE_SIZE_MB` | ❌ | Max upload size (default: `10`) |
| `ALLOWED_ORIGINS` | ❌ | CORS allowed origins |

---

## 📖 API Documentation

Once the backend is running, access the interactive API docs:

- **Swagger UI** → [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc** → [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/cv/upload` | Upload one or more CVs |
| `GET` | `/api/cv/` | List all CVs |
| `POST` | `/api/jobs/` | Create a job post |
| `POST` | `/api/jobs/extract` | Extract job info from document |
| `GET` | `/api/jobs/` | List all job posts |
| `POST` | `/api/analysis/batch` | Launch batch RAG ranking |
| `POST` | `/api/analysis/deep` | Launch LangGraph deep analysis |
| `GET` | `/api/analysis/{id}/report` | Get analysis report |
| `GET` | `/api/analysis/{id}/pdf` | Download PDF report |
| `GET` | `/health` | Health check |

---

## ⚙️ Pipeline Details

The analysis pipeline operates in two phases:

### Phase 1 — RAG Pre-Ranking

```mermaid
flowchart LR
    A[Job Post] --> B[Section Extraction]
    C[CVs] --> D[Section Extraction]
    B --> E[ChromaDB Indexing]
    D --> E
    E --> F[Semantic Similarity]
    F --> G[Weighted Score]
    G --> H[Candidate Ranking]
```

Each document is split into **4 normalized sections** (Competences, Experience, Education, Profile) and embedded using `FastEmbed`. Section-level cosine similarity produces weighted RAG scores.

### Phase 2 — LangGraph Deep Analysis

```mermaid
flowchart TD
    A[START] --> B[🔧 Extract Skills]
    B --> C[🔍 Match CV ↔ Job]
    C --> D[📊 Multi-Criteria Scoring]
    D --> E[📝 Generate Report]
    E --> F[🛡️ Guardrail Validation]
    F -->|✅ Valid| G[END]
    F -->|🔄 Retry| D
    F -->|⚠️ Force End| G
```

The hybrid score combines:
- **70%** LLM qualitative assessment
- **30%** RAG semantic similarity

Final weighted score:
- **Competences**: 40% · **Experience**: 30% · **Education**: 20% · **Soft Skills**: 10%

---

## 📸 Screenshots

<p align="center">
  <img src="docs/images/dashboard_preview.png" alt="Dashboard Preview" width="700"/>
  <br/>
  <em>Dashboard — Overview of recruitment analytics</em>
</p>

---

## 📄 License

This project is developed as an academic/professional project. All rights reserved.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/SeddikBm">Seddik Bm</a>
</p>
