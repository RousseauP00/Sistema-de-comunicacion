# Dockerfile

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copiar solo el código fuente (no el dataset)
COPY producers/   producers/
COPY consumers/   consumers/
COPY scripts/     scripts/
COPY docker-compose.yml .
COPY .dockerignore .

CMD ["bash"]
