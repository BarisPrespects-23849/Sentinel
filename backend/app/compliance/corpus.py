"""A small, real, cited regulatory corpus -- NOT a complete or authoritative
compliance database. This is a representative sample sized for a hackathon
demo, covering exactly the permit types and hazards our seeded zones exercise
(hot work, confined space, flammable-gas testing).

Two source_type values, and the distinction matters:
  - "statute_verbatim": exact quoted text of a numbered legal section
    (The Factories Act, 1948), sourced from Indian Kanoon's bare-act text.
  - "standard_summary": a paraphrased description of what an industry
    standard (OISD-STD-105) or common safety practice requires, based on
    secondary sources -- NOT a verbatim quote of the primary document, which
    isn't freely available online. Presenting this as exact regulatory
    wording would be misleading, so it's labeled distinctly and the
    Compliance Agent's prompt is told to treat citations accordingly.

A real deployment would replace this with a licensed, complete corpus and a
proper document-ingestion pipeline (Milestone 6 built the RAG *pattern*, not
a compliance database).

Each excerpt also carries two ORGANIZATIONAL tags (added for the regulatory
coverage view -- they classify the existing text, they do not add any):
  - "body": the regulatory body it comes from ("OISD" | "Factory Act").
    OISD and the Factories Act 1948 are the primary bodies for this
    petroleum/factory context. (No DGMS excerpts exist here; DGMS governs
    mines, and none were sourced -- the coverage view says so plainly.)
  - "hazard_category": the specific hazard the excerpt addresses, assigned
    from its actual content (e.g. confined_space, gas_testing,
    ignition_control, work_permits).
"""

CORPUS = [
    {
        "id": "factories-act-36-1",
        "citation": "The Factories Act, 1948 (India) -- Section 36(1)",
        "source_type": "statute_verbatim",
        "body": "Factory Act",
        "hazard_category": "confined_space",
        "text": (
            "No person shall be required or allowed to enter any chamber, tank, vat, "
            "pit, pipe, flue or other confined space in any factory in which any gas, "
            "fume, vapour or dust is likely to be present to such an extent as to "
            "involve risk to persons being overcome thereby, unless it is provided "
            "with a manhole of adequate size or other effective means of egress."
        ),
    },
    {
        "id": "factories-act-36-2a",
        "citation": "The Factories Act, 1948 (India) -- Section 36(2)(a)",
        "source_type": "statute_verbatim",
        "body": "Factory Act",
        "hazard_category": "gas_testing",
        "text": (
            "No person shall be required or allowed to enter any confined space "
            "until all practicable measures have been taken to remove any gas, fume, "
            "vapour or dust which may be present so as to bring its level within "
            "permissible limits, unless a certificate in writing has been given by a "
            "competent person, based on a test carried out by himself, that the "
            "space is reasonably free from dangerous gas, fume, vapour or dust."
        ),
    },
    {
        "id": "factories-act-36a",
        "citation": "The Factories Act, 1948 (India) -- Section 36A",
        "source_type": "statute_verbatim",
        "body": "Factory Act",
        "hazard_category": "ignition_control",
        "text": (
            "No portable electric light or any other electric appliance of voltage "
            "exceeding twenty-four volts shall be permitted for use inside any "
            "chamber, tank, vat, pit, pipe, flue or other confined space unless "
            "adequate safety devices are provided; and if any inflammable gas, fume "
            "or dust is likely to be present in such confined space, no lamp or "
            "light other than one of flame-proof construction shall be permitted to "
            "be used therein."
        ),
    },
    {
        "id": "oisd-std-105-permit-types",
        "citation": "OISD-STD-105, Work Permit System (summary, not verbatim)",
        "source_type": "standard_summary",
        "body": "OISD",
        "hazard_category": "work_permits",
        "text": (
            "OISD-STD-105 governs the work permit system at petroleum and hazardous "
            "process facilities, defining cold work, hot work, confined space "
            "entry, and electrical isolation permits. A Confined Space Entry Permit "
            "must be supplemented with a Hot Work or Cold Work Permit corresponding "
            "to the type of work actually being performed inside the space -- a "
            "confined space entry alone does not authorize hot work within it."
        ),
    },
    {
        "id": "gas-testing-practice",
        "citation": "Common Indian industrial gas-testing practice (summary, referencing OISD-STD-114)",
        "source_type": "standard_summary",
        "body": "OISD",
        "hazard_category": "gas_testing",
        "text": (
            "Before hot work begins in a classified hazardous area, the atmosphere "
            "must be tested and certified gas-free by a competent person. Flammable "
            "gas concentration is measured against the Lower Explosive Limit (LEL) "
            "-- the minimum concentration capable of ignition -- and work should not "
            "proceed if readings approach a fraction of the LEL. Oxygen must remain "
            "within the safe range of 19.5%-23.5%. Testing is required before "
            "starting hot work, periodically during the work, and after any break "
            "or change in conditions."
        ),
    },
]
