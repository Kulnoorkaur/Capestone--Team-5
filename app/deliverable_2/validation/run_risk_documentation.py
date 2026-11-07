import json
import streamlit as st

from app.deliverable_2.questionnaires.risk_documentation import (
    render_risk_documentation,
    FIELD_LABELS,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Regulatory Readiness Platform",
    layout="wide"
)


# ============================================================
# HEADER
# ============================================================

st.caption("IMAGING AI | REGULATORY GUIDANCE")

st.title("AI Regulatory Readiness Platform")

st.info(
    "Complete the risk, cybersecurity, and documentation "
    "questionnaire. The information collected will support "
    "subsequent regulatory pathway assessment."
)


# ============================================================
# QUESTIONNAIRE
# ============================================================

profile = render_risk_documentation()


# ============================================================
# REQUIRED FIELDS
# ============================================================

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


# ============================================================
# VALIDATION FUNCTIONS
# ============================================================

def is_missing(value):
    """Identify unanswered fields."""

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
    Check required and conditional information.

    Returns a list of issues requiring attention.
    """

    issues = []

    # Check required fields

    for field_id in REQUIRED_FIELDS:

        if is_missing(profile.get(field_id)):

            issues.append({
                "field_id": field_id,
                "field": FIELD_LABELS.get(field_id, field_id),
                "issue": "Required information is missing",
                "type": "missing"
            })

    # Check conditional fields

    conditional_fields = {
        "RCD-005": "RCD-005-DETAILS",
        "RCD-006": "RCD-006-DETAILS",
        "CYB-002": "CYB-002-OTHER",
        "DOC-004": "DOC-004-DETAILS",
    }

    for parent, child in conditional_fields.items():

        parent_value = profile.get(parent)

        requires_details = (
            parent_value == "Other"
            or (
                parent == "DOC-004"
                and parent_value ==
                "Authorized / cleared / approved in at least one jurisdiction"
            )
            or (
                parent in ["RCD-005", "RCD-006"]
                and parent_value not in [
                    "Select an option",
                    "Not established",
                    "Unknown",
                    None
                ]
            )
            or (
                parent == "CYB-002"
                and isinstance(parent_value, list)
                and "Other" in parent_value
            )
        )

        if requires_details and is_missing(profile.get(child)):

            issues.append({
                "field_id": child,
                "field": "Additional information",
                "issue": "Additional details are required",
                "type": "conditional"
            })

    # Check uncertain information

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
                "type": "uncertain"
            })

    return issues


# ============================================================
# PROFILE PREVIEW
# ============================================================

st.divider()

if st.button("Preview Risk and Documentation Profile", type="primary"):

    issues = validate_profile(profile)

    st.session_state["risk_profile"] = profile.copy()

    st.session_state["risk_validation_issues"] = issues


# ============================================================
# PROFILE SUMMARY
# ============================================================

if "risk_profile" in st.session_state:

    saved_profile = st.session_state["risk_profile"]

    issues = st.session_state["risk_validation_issues"]

    st.divider()

    st.subheader("Risk and Documentation Profile Summary")

    if issues:

        st.warning("manual regulatory review required")

        st.markdown("### Information Requiring Attention")

        for issue in issues:

            st.write(
                f"**{issue['field']} ({issue['field_id']}):** "
                f"{issue['issue']}"
            )

    else:

        st.success(
            "All currently required profile information "
            "has been provided."
        )

    # Display profile information

    st.markdown("### Product Risk and Documentation Information")

    for field_id, response in saved_profile.items():

        label = FIELD_LABELS.get(field_id)

        if label is None:
            label = field_id.replace("-", " ").title()

        if is_missing(response):

            display_value = "Not provided"

        elif isinstance(response, list):

            display_value = ", ".join(response)

        else:

            display_value = response

        st.write(f"**{label}:** {display_value}")

    st.caption(
        "This is a preliminary information-completeness "
        "assessment only. No regulatory classification, "
        "compliance, or readiness determination has been performed."
    )

    # ========================================================
    # JSON EXPORT
    # ========================================================

    export_data = {
        "profile": saved_profile,
        "validation": {
            "manual_review_required": len(issues) > 0,
            "issues": issues
        }
    }

    json_data = json.dumps(
        export_data,
        indent=4,
        ensure_ascii=False
    )

    st.download_button(
        label="Download Risk and Documentation Profile",
        data=json_data,
        file_name="risk_documentation_profile.json",
        mime="application/json"
    )