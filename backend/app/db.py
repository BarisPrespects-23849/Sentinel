"""Shared PostgreSQL connection helper, used by the ingest service and
(later) the FastAPI app itself."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# backend/app/db.py -> repo root is two directories up.
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )
