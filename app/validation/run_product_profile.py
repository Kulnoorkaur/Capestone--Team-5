import json
import streamlit as st

from product_profile import render_product_profile, FIELD_LABELS


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
    "Complete the product and intended-use questionnaire. "
    "The information collected will support subsequent "
    "regulatory pathway assessment."
)


# ============================================================
# QUESTIONNAIRE
# ============================================================

profile = render_product_profile()


# ============================================================
# REQUIRED FIELDS
# ============================================================

# Preliminary prototype requirements.
# Final requirements must align with the D2.1 data dictionary.

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
    "PIP-023"
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
        "PIP-006": "PIP-006-OTHER",
        "PIP-017": "PIP-017-OTHER"
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
                    "type": "conditional"
                })

    # Check multi-select Other options

    multi_other_fields = {
        "PIP-007": "PIP-007-OTHER",
        "PIP-016": "PIP-016-OTHER",
        "PIP-022": "PIP-022-OTHER"
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
                    "type": "conditional"
                })

    # Specialized training

    if profile.get("PIP-009") == "Yes":

        if is_missing(profile.get("TRAINING-DETAILS")):

            issues.append({
                "field_id": "TRAINING-DETAILS",
                "field": "Specialized Training",
                "issue": "Training details are required",
                "type": "conditional"
            })

    elif profile.get("PIP-009") == "Unknown":

        issues.append({
            "field_id": "PIP-009",
            "field": "Specialized Training Required",
            "issue": "Training requirements are unknown",
            "type": "uncertain"
        })

    # Time-critical status

    if profile.get("PIP-018") == "Unknown":

        issues.append({
            "field_id": "PIP-018",
            "field": "Routine or Time-Critical Use",
            "issue": "Clinical urgency has not been determined",
            "type": "uncertain"
        })

    return issues


# ============================================================
# PROFILE PREVIEW
# ============================================================

st.divider()

if st.button("Preview Product Profile", type="primary"):

    issues = validate_profile(profile)

    st.session_state["product_profile"] = profile.copy()

    st.session_state["validation_issues"] = issues


# ============================================================
# PROFILE SUMMARY
# ============================================================

if "product_profile" in st.session_state:

    saved_profile = st.session_state["product_profile"]

    issues = st.session_state["validation_issues"]

    st.divider()
    st.subheader("Product Profile Summary")

    if issues:

        st.warning(
            "Manual regulatory review required. "
            "Some information is missing, conditional, "
            "or uncertain."
        )

        st.markdown("### Information Requiring Attention")

        for issue in issues:

            st.write(
                f"**{issue['field']}:** {issue['issue']}"
            )

    else:

        st.success(
            "All currently required product-profile "
            "information has been provided."
        )

    # Display user-friendly summary

    st.markdown("### Product Information")

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
        "assessment only. No regulatory classification "
        "or readiness determination has been performed."
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
        label="Download Product Profile",
        data=json_data,
        file_name="product_profile.json",
        mime="application/json"
    )
