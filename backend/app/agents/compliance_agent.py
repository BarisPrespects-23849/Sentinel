"""Compliance Agent: RAG over a small Indian industrial safety regulatory
corpus (see app/compliance/corpus.py), with grounded narrative generation
via the Gemini API.

Uses Gemini rather than Claude for this one agent -- a deliberate deviation
from the project's original "LLM: Claude API" architecture decision, made
by the project owner mid-build. See README for the reasoning.

This agent is purely informational: it explains WHY a situation might be
regulation-relevant, citing real source text, but does not add numeric
risk points -- that would double-count with the Permit Agent's scoring.
Only runs the (paid) LLM call when there's something to comment on: an
active permit or an elevated sensor reading. A fully calm zone costs
nothing and returns no signal.
"""

import logging
import os
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.agents.state import AgentState
from app.compliance.ingest import CHROMA_PATH, COLLECTION_NAME, build_index

# backend/app/agents/compliance_agent.py -> repo root is four directories up.
load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

TOP_K = 3
# Free-tier Gemini quotas are PER MODEL PER DAY (observed: 20/day for
# gemini-3.5-flash). The fallback model has its own separate quota, so a
# quota-exhausted primary degrades to the fallback instead of failing --
# without this, a busy demo day kills the narrative feature entirely.
MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]
# Hard ceiling on the LLM call so a hung upstream can never stall the whole
# multi-agent assessment. google-genai's HttpOptions.timeout is milliseconds.
LLM_TIMEOUT_MS = 20_000

# Situations repeat heavily (same zone, same permit, same elevated types),
# so successful narratives are cached to conserve the daily quota. Only
# successes are cached -- failures must stay retryable on the next click.
CACHE_TTL_SECONDS = 600
_narrative_cache: dict[str, tuple[float, str]] = {}

SYSTEM_INSTRUCTION = (
    "You are a compliance assistant for an industrial safety platform. You will be "
    "given a situation description and several retrieved regulatory text excerpts. "
    "Write a 2-3 sentence compliance note explaining which excerpt(s) are relevant "
    "and why, citing them by name. Only use facts present in the provided excerpts "
    "-- do not invent regulation numbers, thresholds, or requirements not stated "
    "there. If none of the excerpts are clearly relevant, say so plainly instead of "
    "stretching a citation to fit."
)


def _get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        return build_index()


_collection = _get_collection()

# The Gemini client is created lazily on first use, NOT at import time.
# A missing/invalid key must degrade this one agent, never prevent the
# whole backend (sensor monitoring included) from starting.
_genai_client = None
_genai_client_failed = False


def _get_genai_client():
    global _genai_client, _genai_client_failed
    if _genai_client is None and not _genai_client_failed:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            _genai_client_failed = True
            logger.warning("GEMINI_API_KEY not set -- compliance narrative disabled")
        else:
            try:
                _genai_client = genai.Client(
                    api_key=api_key,
                    http_options=types.HttpOptions(timeout=LLM_TIMEOUT_MS),
                )
            except Exception:
                _genai_client_failed = True
                logger.exception("Failed to initialize Gemini client")
    return _genai_client


def _unavailable_signal(citations: list[str], reason: str) -> dict:
    """Degraded-mode signal: the assessment still succeeds, the retrieved
    citations are still surfaced, and the narrative's absence is explicit
    rather than silent."""
    return {
        "source": "compliance",
        "sensor_id": None,
        "sensor_type": None,
        "description": (
            f"Compliance narrative unavailable ({reason}). The retrieved "
            "regulations listed below may still apply -- review them manually."
        ),
        "weight_contribution": 0,
        "citations": citations,
        "degraded": True,
    }


def _generate_narrative(client, situation: str, prompt: str) -> tuple[str | None, str]:
    """Returns (narrative, failure_reason). Tries each model in MODELS:
    - transient server error (5xx) -> one retry on the same model
    - quota exhausted (429) -> NO retry (daily quota), next model instead
    Successful narratives are cached by situation for CACHE_TTL_SECONDS to
    conserve the small free-tier daily quotas."""
    cached = _narrative_cache.get(situation)
    if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1], ""

    reason = "LLM call failed or timed out"
    for model in MODELS:
        for attempt in (1, 2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION
                    ),
                )
                description = (response.text or "").strip()
                if not description:
                    raise ValueError("empty LLM response")
                _narrative_cache[situation] = (time.monotonic(), description)
                return description, ""
            except genai_errors.ClientError as exc:
                # 4xx: retrying the same request cannot help. 429 means this
                # model's daily quota is gone -- move to the next model.
                if getattr(exc, "code", None) == 429:
                    logger.warning("Quota exhausted for %s -- trying next model", model)
                    reason = "LLM daily quota exhausted"
                else:
                    logger.exception("Gemini client error on %s", model)
                break
            except Exception:
                logger.exception("Gemini call failed (%s, attempt %d)", model, attempt)
    return None, reason


def make_compliance_agent(conn):
    def compliance_agent(state: AgentState) -> dict:
        sensor_result = state.get("sensor_result") or {}
        elevated_types = sorted({
            sig["sensor_type"]
            for sig in sensor_result.get("contributing_signals", [])
            if sig.get("source") == "rule" and sig.get("sensor_type")
        })

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT permit_type FROM permits
                WHERE zone_id = %s AND status = 'active'
                  AND now() BETWEEN valid_from AND valid_until
                """,
                (state["zone_id"],),
            )
            permit_types = sorted(row[0] for row in cur.fetchall())

        if not elevated_types and not permit_types:
            return {"compliance_result": {"signals": []}}

        query_parts = []
        if permit_types:
            query_parts.append(f"active {', '.join(permit_types)} permit(s)")
        if elevated_types:
            query_parts.append(f"elevated {', '.join(elevated_types)} sensor readings")
        situation = " and ".join(query_parts) + " in an industrial zone"

        # Retrieval failure is survivable too -- degrade, don't 500.
        try:
            results = _collection.query(query_texts=[situation], n_results=TOP_K)
            docs = results["documents"][0]
            metas = results["metadatas"][0]
        except Exception:
            logger.exception("ChromaDB retrieval failed")
            signal = _unavailable_signal([], "regulation index unavailable")
            return {"compliance_result": {"signals": [signal]}}

        citations = [m["citation"] for m in metas]

        client = _get_genai_client()
        if client is None:
            signal = _unavailable_signal(citations, "LLM not configured")
            return {"compliance_result": {"signals": [signal]}}

        context_block = "\n\n".join(
            f"[{m['citation']}]: {d}" for d, m in zip(docs, metas)
        )
        prompt = (
            f"Situation: {situation}.\n\n"
            f"Retrieved regulatory excerpts:\n\n{context_block}\n\n"
            "Write your compliance note now."
        )

        description, reason = _generate_narrative(client, situation, prompt)
        if not description:
            signal = _unavailable_signal(citations, reason)
            return {"compliance_result": {"signals": [signal]}}

        signal = {
            "source": "compliance",
            "sensor_id": None,
            "sensor_type": None,
            "description": description,
            "weight_contribution": 0,
            "citations": citations,
        }
        return {"compliance_result": {"signals": [signal]}}

    return compliance_agent
