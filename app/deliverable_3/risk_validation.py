"""Reusable Deliverable 2.5 validation logic."""

from app.deliverable_2.questionnaires.risk_documentation import FIELD_LABELS


REQUIRED_FIELDS = [
    "RCD-001",
    "RCD-002",
    "RCD-007",
    "CYB-001",
    "CYB-003",
    "UID-001",
    "DOC-001",
    "DOC-002",
    "DOC-003",
    "DOC-004",
]


def is_missing(value):
    """Identify unanswered fields."""

    if value is None:
        return True

    if isinstance(value, str):
        return value.strip() == "" or value == "Select an option"

    if isinstance(value, list):
        return len(value) == 0

    return False


def validate_risk_documentation(profile):
    """Validate D2.5 responses and return structured issues."""

    issues = []

    # Required fields
    for field_id in REQUIRED_FIELDS:
        if is_missing(profile.get(field_id)):
            issues.append({
                "field_id": field_id,
                "field": FIELD_LABELS.get(field_id, field_id),
                "issue": "Required information is missing",
                "type": "missing",
            })

    # Conditional fields
    conditional_rules = {
        "RCD-005": (
            ["Numerical scale", "Other defined scale"],
            "RCD-005-DETAILS",
        ),
        "RCD-006": (
            [
                "Qualitative categories",
                "Numerical probability",
                "Other defined method",
            ],
            "RCD-006-DETAILS",
        ),
        "DOC-004": (
            ["Authorized / cleared / approved in at least one jurisdiction"],
            "DOC-004-DETAILS",
        ),
    }

    for parent, (trigger_values, child) in conditional_rules.items():
        if profile.get(parent) in trigger_values and is_missing(profile.get(child)):
            issues.append({
                "field_id": child,
                "field": FIELD_LABELS.get(parent, parent),
                "issue": "Additional details are required",
                "type": "conditional",
            })

    if (
        "Other" in profile.get("CYB-002", [])
        and is_missing(profile.get("CYB-002-OTHER"))
    ):
        issues.append({
            "field_id": "CYB-002-OTHER",
            "field": FIELD_LABELS["CYB-002"],
            "issue": "Additional details are required",
            "type": "conditional",
        })

    # Uncertain responses
    uncertain_fields = [
        "RCD-001",
        "CYB-001",
        "CYB-003",
        "UID-001",
        "DOC-001",
        "DOC-002",
        "DOC-003",
        "DOC-004",
    ]

    for field_id in uncertain_fields:
        if profile.get(field_id) == "Unknown":
            issues.append({
                "field_id": field_id,
                "field": FIELD_LABELS.get(field_id, field_id),
                "issue": "Information has not been determined",
                "type": "uncertain",
            })

    return issues
