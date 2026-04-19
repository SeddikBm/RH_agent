FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances système (pour PyMuPDF et WeasyPrint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libcairo2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copier le code source
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/data/uploads /app/chroma_db

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
