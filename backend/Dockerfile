# One image, three services: the API (default command), the sensor
# simulator, and the MQTT->TimescaleDB ingest worker. docker-compose.yml
# overrides `command` for the latter two -- same code, same dependencies,
# no image duplication.

FROM python:3.12-slim

# Unbuffered stdout so `docker compose logs` streams in real time.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/sentinel

# Dependencies first: this layer only rebuilds when requirements.txt
# changes, so day-to-day code edits rebuild in seconds.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Bake the demo-critical artifacts into the image at BUILD time:
# - the trained risk model (otherwise trained lazily on first request)
# - the ChromaDB regulation index, which downloads its embedding model
#   (~80MB) on first use.
# A hackathon venue's wifi must never be a runtime dependency.
RUN python -m app.risk.train_model && \
    python -m app.compliance.ingest

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
