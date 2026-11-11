# ============================================================
# DELIVERABLE 3.1: PRODUCT PROFILE VALIDATION
# ============================================================

from app.deliverable_2.questionnaires.product_profile import FIELD_LABELS


# Preliminary requirements from Deliverable 2.1.
# Final requirements must be reconciled with the D2.1
# data dictionary and Deliverable 2.6.

REQUIRED_FIELDS = [
    "PIP-001",
    "PIP-002",
    "PIP-003",
    "PIP-004",
    "PIP-005",
    "PIP-006",
    "PIP-007",
    "PIP-008",
    "PIP-012",
    "PIP-016",
    "PIP-020",
    "PIP-023",
]


def is_missing(value):
    """Identify unanswered questionnaire fields."""

    if value is None:
        return True

    if isinstance(value, str):
        return (
            value.strip() == ""
            or value == "Select an option"
        )

    if isinstance(value, list):
        return len(value) == 0

    return False


def validate_profile(profile):
    """
    Validate product-profile completeness and selected
    conditional or uncertain responses.

    Returns a list of validation issues.
    """

    issues = []

    # --------------------------------------------------------
    # 1. REQUIRED FIELDS
    # --------------------------------------------------------

    for field_id in REQUIRED_FIELDS:

        if is_missing(profile.get(field_id)):

            issues.append({
                "field_id": field_id,
                "field": FIELD_LABELS.get(field_id, field_id),
                "issue": "Required information is missing",
                "type": "missing",
            })

    # --------------------------------------------------------
    # 2. CONDITIONAL FIELDS
    # --------------------------------------------------------

    conditional_fields = {
        "PIP-006": "PIP-006-OTHER",
        "PIP-017": "PIP-017-OTHER",
    }

    for parent, child in conditional_fields.items():

        if profile.get(parent) == "Other":

            if is_missing(profile.get(child)):

                issues.append({
                    "field_id": child,
                    "field": "Additional information",
                    "issue": (
                        "An 'Other' option was selected "
                        "without providing details"
                    ),
                    "type": "conditional",
                })

    # --------------------------------------------------------
    # 3. MULTI-SELECT CONDITIONAL FIELDS
    # --------------------------------------------------------

    multi_other_fields = {
        "PIP-007": "PIP-007-OTHER",
        "PIP-016": "PIP-016-OTHER",
        "PIP-022": "PIP-022-OTHER",
    }

    for parent, child in multi_other_fields.items():

        if "Other" in profile.get(parent, []):

            if is_missing(profile.get(child)):

                issues.append({
                    "field_id": child,
                    "field": "Additional information",
                    "issue": (
                        "An 'Other' option was selected "
                        "without providing details"
                    ),
                    "type": "conditional",
                })

    # --------------------------------------------------------
    # 4. SPECIALIZED TRAINING
    # --------------------------------------------------------

    if profile.get("PIP-009") == "Yes":

        if is_missing(profile.get("TRAINING-DETAILS")):

            issues.append({
                "field_id": "TRAINING-DETAILS",
                "field": "Specialized Training",
                "issue": "Training details are required",
                "type": "conditional",
            })

    elif profile.get("PIP-009") == "Unknown":

        issues.append({
            "field_id": "PIP-009",
            "field": "Specialized Training Required",
            "issue": "Training requirements are unknown",
            "type": "uncertain",
        })

    # --------------------------------------------------------
    # 5. TIME-CRITICAL STATUS
    # --------------------------------------------------------

    if profile.get("PIP-018") == "Unknown":

        issues.append({
            "field_id": "PIP-018",
            "field": "Routine or Time-Critical Use",
            "issue": "Clinical urgency has not been determined",
            "type": "uncertain",
        })

    return issues