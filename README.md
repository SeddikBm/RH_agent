# Agent d'Évaluation de Candidatures RH

Un système IA multi-étapes pour l'aide à la décision RH : analyse sémantique de CVs, matching avec des fiches de poste, et génération de rapports explicatifs.

## Stack Technique

| Composant | Technologie |
|:---|:---|
| LLM | GroqCloud — Llama 3.3 70B Versatile |
| Embeddings | Ollama — mxbai-embed-large (local) |
| Vector Store | ChromaDB (persistant) |
| Workflow IA | LangGraph |
| Observabilité | LangSmith |
| Backend | FastAPI (Python 3.11+) |
| Base de données | PostgreSQL 16 |
| Frontend | React 18 + Vite |
| Conteneurisation | Docker + Docker Compose |

## Démarrage Rapide

### 1. Prérequis

- Docker Desktop installé et en cours d'exécution
- Clé API GroqCloud (gratuite : https://console.groq.com)
- Clé API LangSmith (optionnel, pour le traçage : https://smith.langchain.com)

### 2. Configuration

```bash
cp .env.example .env
# Éditez .env et renseignez vos clés API :
# GROQ_API_KEY=gsk_...
# LANGSMITH_API_KEY=lsv2_... (optionnel)
```

### 3. Lancement (Docker)

```bash
docker-compose up --build
```

**Note** : Le premier démarrage télécharge le modèle Ollama `mxbai-embed-large` (~700MB). Patientez jusqu'à voir le log `✅ Agent RH prêt`.

### 4. Accès à l'application

| Service | URL |
|:---|:---|
| Frontend | http://localhost:3000 |
| API FastAPI | http://localhost:8000 |
| Documentation API | http://localhost:8000/api/docs |

## Développement Local (sans Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Démarrez PostgreSQL et Ollama séparément
# Puis :
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Pipeline LangGraph

```
START
  │
  ▼
[Nœud 1] Extraction des Compétences  ← GroqCloud
  │
  ▼
[Nœud 2] Matching CV ↔ Fiche de Poste  ← RAG (ChromaDB + Ollama)
  │
  ▼
[Nœud 3] Scoring Multicritère  ← GroqCloud (40% tech · 30% exp · 20% form · 10% soft)
  │
  ▼
[Nœud 4] Génération du Rapport  ← GroqCloud
  │
  ▼
[Garde-Fou] Validation  ← Pydantic + détection de biais
  │           │
  ▼           ▼
 END        retry → [Nœud 3]
```

## Structure du Projet

```
AI_Agent/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # FastAPI app
│   ├── config.py            # Pydantic Settings
│   ├── api/routes/          # cv.py, job.py, analysis.py
│   ├── models/              # schemas.py, database.py
│   ├── services/            # parser.py, llm.py, rag.py
│   ├── agents/              # state.py, graph.py, nodes/
│   └── guardrails/          # validators.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── pages/           # Dashboard, Upload, Analyses, Report, Jobs
│       ├── components/      # Layout
│       └── api/             # client.js
└── data/
    ├── sample_cvs/          # CVs fictifs de test
    └── sample_jobs/         # Fiches de poste fictives
```

## Disclaimer

⚠️ **Ce système est un outil d'aide à la décision RH.** Il ne remplace en aucun cas le jugement d'un professionnel RH qualifié. Toute décision de recrutement reste sous la responsabilité exclusive de l'équipe humaine de recrutement.
