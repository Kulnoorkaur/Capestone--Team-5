"""Preliminary D2.2 completeness, conditional, and clarification checks.

These checks are not regulatory classification or readiness decisions.
Confirm REQUIRED_FIELDS against the team's finalized D2.2 data dictionary.
"""
# from ai_function import FIELD_LABELS, render_ai_function
from app.deliverable_2.questionnaires.ai_function import FIELD_LABELS
import streamlit as st
# REQUIRED FIELDS

# PROVISIONAL: Confirm required/conditional status in D2.2 data dictionary.

REQUIRED_FIELDS = [
    "AIF-001", "AIF-002", "AIF-003", "AIF-004", "AIF-005",
    "AIF-006", "AIF-007", "AIF-008", "AIF-010", "AIF-011",
    "AIF-012", "AIF-013", "AIF-014", "AIF-015", "AIF-016",
    "AIF-017", "AIF-018", "AIF-019", "AIF-020",
]


# ============================================================
# READINESS GATE MAPPING
# ============================================================

GATE_MAPPING = {
    "AIF-001": ["G1", "G2"],
    "AIF-002": ["G1", "G2"],
    "AIF-003": ["G1", "G2"],
    "AIF-004": ["G1", "G2"],
    "AIF-005": ["G1", "G2"],
    "AIF-006": ["G1", "G2"],
    "AIF-007": ["G1", "G2"],
    "AIF-008": ["G1", "G2"],
    "AIF-009": ["G1", "G2", "G7"],
    "AIF-010": ["G1", "G2"],
    "AIF-011": ["G1", "G2"],
    "AIF-012": ["G1", "G2"],
    "AIF-013": ["G1", "G2", "G4"],
    "AIF-014": ["G1", "G2"],
    "AIF-015": ["G1", "G2"],
    "AIF-016": ["G1", "G2"],
    "AIF-017": ["G1", "G2"],
    "AIF-018": ["G1", "G2", "G4", "G7"],
    "AIF-019": ["G1", "G2", "G4"],
    "AIF-020": ["G1", "G2", "G4", "G7"],
}


# ============================================================
# MISSING INFORMATION CHECK
# ============================================================

def is_missing(value):
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip() or value == "Select an option"

    if isinstance(value, list):
        return len(value) == 0

    return False


# ============================================================
# QUESTIONNAIRE VALIDATION
# ============================================================

def validate_ai_function(profile):
    """Return structured issues; no pass/fail regulatory decision."""

    issues = []
    seen = set()

    def add(field_id, issue, issue_type):

        identity = (field_id, issue_type, issue)

        if identity in seen:
            return

        seen.add(identity)

        issues.append({
            "field_id": field_id,
            "field": FIELD_LABELS.get(field_id, field_id),
            "issue": issue,
            "type": issue_type,
            "relevant_gates": GATE_MAPPING.get(
                field_id.split("-OTHER")[0].split("-DETAILS")[0], []
            ),
        })

    # ========================================================
    # CHECK REQUIRED FIELDS
    # ========================================================

    for field_id in REQUIRED_FIELDS:

        if is_missing(profile.get(field_id)):
            add(
                field_id,
                "Required information has not been provided.",
                "missing"
            )

    # ========================================================
    # CHECK 'OTHER' FOLLOW-UP QUESTIONS
    # ========================================================

    for parent in (
        "AIF-001",
        "AIF-003",
        "AIF-006",
        "AIF-007",
        "AIF-009",
        "AIF-012",
        "AIF-018",
        "AIF-020"
    ):

        if "Other" in profile.get(parent, []):

            if is_missing(profile.get(f"{parent}-OTHER")):
                add(
                    parent,
                    "'Other' was selected without specifying details.",
                    "conditional"
                )

    # ========================================================
    # CHECK CONDITIONAL EXPLANATIONS
    # ========================================================

    for parent, expected in (
        ("AIF-005", ("Yes",)),
        ("AIF-014", ("Yes", "Sometimes")),
        ("AIF-016", ("Always", "Sometimes", "Never")),
        ("AIF-017", ("Yes", "Partly", "No")),
        ("AIF-019", ("Yes",)),
    ):

        if (
            profile.get(parent) in expected
            and is_missing(profile.get(f"{parent}-DETAILS"))
        ):
            add(
                parent,
                "A follow-up explanation is required for this answer.",
                "conditional"
            )

    # ========================================================
    # CHECK UNKNOWN RESPONSES
    # ========================================================

    for field_id in FIELD_LABELS:

        value = profile.get(field_id)

        if value == "Unknown" or (
            isinstance(value, list) and "Unknown" in value
        ):
            add(
                field_id,
                "The response is unknown and may need clarification.",
                "uncertain"
            )

        elif isinstance(value, str) and value.strip().lower() == "unknown":
            add(
                field_id,
                "The response is unknown and may need clarification.",
                "uncertain"
            )

    # ========================================================
    # CHECK INCONSISTENT MULTIPLE-CHOICE ANSWERS
    # ========================================================

    for field_id in ("AIF-009", "AIF-018"):

        selections = profile.get(field_id, [])

        if "None" in selections and len(selections) > 1:
            add(
                field_id,
                "'None' was selected together with another option; "
                "please clarify.",
                "consistency"
            )

    for field_id in ("AIF-009", "AIF-020"):

        selections = profile.get(field_id, [])

        if "Unknown" in selections and len(selections) > 1:
            add(
                field_id,
                "'Unknown' was selected together with a specific option; "
                "please clarify.",
                "consistency"
            )

    # ========================================================
    # MANUAL REVIEW FLAGS
    # ========================================================

    # Automated clinical or workflow actions

    if profile.get("AIF-019") == "Yes":

        add(
            "AIF-019",
            "Actions without human approval need further review "
            "of workflow and safeguards.",
            "review"
        )

    # Limited independent assessment

    if profile.get("AIF-017") in ("No", "Partly"):

        add(
            "AIF-017",
            "Independent assessment of the output may be limited; "
            "review the clinical role.",
            "review"
        )

    # Potential inconsistency between clinician review and automation

    if (
        profile.get("AIF-016") == "Always"
        and profile.get("AIF-019") == "Yes"
    ):

        add(
            "AIF-019",
            "Clarify how automated actions relate to clinician "
            "review before clinical action; these answers are "
            "not necessarily contradictory.",
            "consistency"
        )

    return issues
