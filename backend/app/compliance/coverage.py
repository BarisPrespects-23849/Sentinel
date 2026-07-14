"""Read-only regulatory-coverage summary derived from the indexed corpus.

Additive and organizational: it classifies what `CORPUS` already contains
and adds no regulatory text. The honest framing is baked in:

  - PRIMARY bodies for this petroleum/factory facility: OISD and the
    Factories Act 1948. These are the applicable regulators for the demo
    scenario, so they are the core coverage.
  - DGMS governs MINES, not factories/refineries. It is surfaced ONLY as a
    labeled mining-context adjacency -- never as governing the demo facility.
    No DGMS excerpts were sourced for this corpus, so the summary reports its
    coverage as empty rather than implying coverage that does not exist.

The whole corpus is a DEMONSTRATION set that proves citation-grounded
retrieval -- not a complete or authoritative compliance reference.
"""

from app.compliance.corpus import CORPUS

# Bodies applicable to this facility type (petroleum / factory context).
PRIMARY_BODIES = ["Factory Act", "OISD"]
# Named for honesty/completeness, but NOT governing this facility -- see note.
ADJACENCY_BODIES = ["DGMS"]

DEMONSTRATION_NOTE = (
    "Demonstration corpus proving citation-grounded retrieval -- NOT a "
    "complete or authoritative compliance reference."
)

SOURCE_TYPE_LEGEND = {
    "statute_verbatim": "Exact quoted text of a numbered legal section.",
    "standard_summary": "Paraphrased summary of a standard's requirement (not verbatim).",
}


def _excerpts_for(body: str) -> list[dict]:
    return [
        {
            "citation": c["citation"],
            "hazard_category": c["hazard_category"],
            "source_type": c["source_type"],
        }
        for c in CORPUS
        if c["body"] == body
    ]


def _block(body: str) -> dict:
    items = _excerpts_for(body)
    return {
        "body": body,
        "count": len(items),
        "hazard_categories": sorted({i["hazard_category"] for i in items}),
        "excerpts": items,
    }


def coverage_summary() -> dict:
    """The full coverage summary. Primary bodies list their real excerpts;
    adjacency bodies (DGMS) carry an explicit note and, here, zero excerpts."""
    primary = [_block(b) for b in PRIMARY_BODIES]

    adjacency = []
    for body in ADJACENCY_BODIES:
        block = _block(body)
        empty = block["count"] == 0
        block["adjacency_note"] = (
            "DGMS governs mines, not this factory/refinery -- shown as a "
            "mining-context adjacency, not governing coverage of the demo "
            "facility."
            + (" No DGMS excerpts are sourced in this demonstration corpus."
               if empty else "")
        )
        adjacency.append(block)

    return {
        "demonstration_set": True,
        "note": DEMONSTRATION_NOTE,
        "total_excerpts": len(CORPUS),
        "primary_bodies": primary,
        "adjacency_bodies": adjacency,
        "hazard_categories_covered": sorted({c["hazard_category"] for c in CORPUS}),
        "source_type_legend": SOURCE_TYPE_LEGEND,
    }
