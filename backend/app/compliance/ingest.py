"""Builds the local ChromaDB vector index from the regulatory corpus.

Run with:
    python -m app.compliance.ingest
"""

from pathlib import Path

import chromadb

from app.compliance.corpus import CORPUS

CHROMA_PATH = Path(__file__).resolve().parent / "chroma_data"
COLLECTION_NAME = "sentinel_regulations"


def build_index():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # fine on first run -- collection doesn't exist yet

    collection = client.create_collection(COLLECTION_NAME)
    collection.add(
        ids=[c["id"] for c in CORPUS],
        documents=[c["text"] for c in CORPUS],
        metadatas=[
            {
                "citation": c["citation"],
                "source_type": c["source_type"],
                "body": c["body"],
                "hazard_category": c["hazard_category"],
            }
            for c in CORPUS
        ],
    )
    return collection


if __name__ == "__main__":
    collection = build_index()
    print(f"Indexed {collection.count()} regulatory chunks into {CHROMA_PATH}")
