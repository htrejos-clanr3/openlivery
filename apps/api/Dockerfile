FROM python:3.12.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 openlivery \
    && useradd --uid 10001 --gid openlivery --create-home openlivery

WORKDIR /app/backend

COPY requirements.txt ./requirements.txt
COPY requirements-dev.txt ./requirements-dev.txt
COPY pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY app ./app
# Tests stay in the image so `make test` can run them after installing
# requirements-dev; they are not imported by the runtime process.
COPY tests ./tests

RUN mkdir -p /app/backend/storage \
    && chown -R openlivery:openlivery /app

USER openlivery

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
