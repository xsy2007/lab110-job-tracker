FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY snapshots ./snapshots

# data/ is volume-mounted at runtime; evidence/ is written at runtime.
RUN mkdir -p /app/data /app/evidence

EXPOSE 8000

# On start, create_app() runs init_db() + seed_defaults() (user1/user2/maintainer).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
