"""Tests for the tagged regulatory corpus and its coverage summary.

These assert the corpus is well-formed and honestly organized: every
excerpt carries a body + hazard_category (the organizational tags), the
source_type distinction is preserved, and the coverage summary accounts for
every excerpt with DGMS surfaced strictly as a labeled mining adjacency.
"""

from app.compliance.corpus import CORPUS
from app.compliance.coverage import (
    ADJACENCY_BODIES,
    PRIMARY_BODIES,
    coverage_summary,
)

KNOWN_BODIES = set(PRIMARY_BODIES) | set(ADJACENCY_BODIES)


def test_every_excerpt_has_required_fields_and_tags():
    assert len(CORPUS) == 5
    for c in CORPUS:
        # Original fields intact...
        assert c["id"] and c["citation"] and c["text"]
        assert c["source_type"] in {"statute_verbatim", "standard_summary"}
        # ...plus the two organizational tags this task added.
        assert c["body"], f"{c['id']} missing body"
        assert c["hazard_category"], f"{c['id']} missing hazard_category"
        assert c["body"] in KNOWN_BODIES


def test_source_type_distinction_preserved():
    counts = {"statute_verbatim": 0, "standard_summary": 0}
    for c in CORPUS:
        counts[c["source_type"]] += 1
    # The 3 Factory Act sections are verbatim; the 2 OISD entries are summaries.
    assert counts == {"statute_verbatim": 3, "standard_summary": 2}


def test_per_body_breakdown():
    by_body = {}
    for c in CORPUS:
        by_body[c["body"]] = by_body.get(c["body"], 0) + 1
    assert by_body == {"Factory Act": 3, "OISD": 2}


def test_coverage_summary_accounts_for_every_excerpt():
    s = coverage_summary()
    primary_sum = sum(b["count"] for b in s["primary_bodies"])
    adjacency_sum = sum(b["count"] for b in s["adjacency_bodies"])
    # No body silently dropped from the grouping.
    assert primary_sum + adjacency_sum == s["total_excerpts"] == len(CORPUS)


def test_coverage_is_labeled_a_demonstration_set():
    s = coverage_summary()
    assert s["demonstration_set"] is True
    assert "NOT a complete" in s["note"] or "not a complete" in s["note"].lower()


def test_dgms_surfaced_only_as_labeled_adjacency():
    s = coverage_summary()
    primary_names = {b["body"] for b in s["primary_bodies"]}
    adjacency_names = {b["body"] for b in s["adjacency_bodies"]}
    # DGMS must never appear as a primary (governing) body.
    assert "DGMS" not in primary_names
    assert "DGMS" in adjacency_names
    dgms = next(b for b in s["adjacency_bodies"] if b["body"] == "DGMS")
    assert dgms["count"] == 0  # none sourced
    assert "mine" in dgms["adjacency_note"].lower()


def test_hazard_categories_reported():
    s = coverage_summary()
    # Derived from the actual tags -- not hardcoded content.
    expected = sorted({c["hazard_category"] for c in CORPUS})
    assert s["hazard_categories_covered"] == expected


def test_coverage_endpoint(client):
    res = client.get("/compliance/coverage")
    assert res.status_code == 200
    body = res.json()
    assert body["total_excerpts"] == 5
    assert body["demonstration_set"] is True
