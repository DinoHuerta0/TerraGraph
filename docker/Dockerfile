# Imagen de TerraGraph. Se construye desde la raíz del repo:
#   docker build -f docker/Dockerfile -t terragraph .
# Las exclusiones del contexto están en docker/Dockerfile.dockerignore.

# --- Etapa 1: instalar las dependencias en un entorno virtual ---
FROM python:3.12-slim AS builder

# El venv se copia completo a la etapa final; pip y su caché se quedan aquí.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Primero solo requirements.txt: si el código cambia pero las dependencias no,
# Docker reutiliza esta capa y no vuelve a instalar todo.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Etapa 2: imagen final, solo con lo necesario para correr ---
FROM python:3.12-slim

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Usuario y grupo de sistema sin privilegios, con UID y GID fijos para que
# Kubernetes pueda comprobar runAsNonRoot.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# alembic.ini y migrations/ van en la imagen porque el initContainer de
# Kubernetes corre las migraciones con esta misma imagen.
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

# Los archivos quedan del usuario root: la app puede leerlos, pero no modificarlos.
USER 10001:10001

EXPOSE 8000

# Para `docker ps` en local; en Kubernetes se usan las probes del Deployment.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
