import json
import streamlit as st


# QUESTIONNAIRE IMPORT — USE ONE OPTION AT A TIME
# ============================================================

# 1: VS CODE on laptop
# Uncomment if ai_function.py is in the same folder as this file.
# from ai_function import FIELD_LABELS, render_ai_function

# 2: GITHUB CODESPACES 
# Use when ai_function.py is in app/deliverable_2/questionnaires/
# and this file is in app/deliverable_2/validation/
from app.deliverable_2.questionnaires.ai_function import FIELD_LABELS, render_ai_function


# REQUIRED FIELDS
# ============================================================
# All 20 fields are marked Required in the current D2.2 data dictionary.
# Confirm this list again if the team revises the data dictionary.

REQUIRED_FIELDS = [
    "AIF-001", "AIF-002", "AIF-003", "AIF-004", "AIF-005",
    "AIF-006", "AIF-007", "AIF-008", "AIF-009", "AIF-010", "AIF-011",
    "AIF-012", "AIF-013", "AIF-014", "AIF-015", "AIF-016",
    "AIF-017", "AIF-018", "AIF-019", "AIF-020",
]


# READINESS GATE MAPPING
# ============================================================
# Informational mapping only; this is NOT a gate-readiness decision.

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

    
    # CHECK REQUIRED FIELDS
    # ========================================================

    for field_id in REQUIRED_FIELDS:
        if is_missing(profile.get(field_id)):
            add(
                field_id,
                "Required information has not been provided.",
                "missing"
            )

    
    # CHECK 'OTHER' FOLLOW-UP QUESTIONS
    # ========================================================

    for parent in (
        "AIF-001", "AIF-003", "AIF-006", "AIF-007",
        "AIF-009", "AIF-012", "AIF-018", "AIF-020"
    ):
        if "Other" in profile.get(parent, []):
            if is_missing(profile.get(f"{parent}-OTHER")):
                add(
                    parent,
                    "'Other' was selected without specifying details.",
                    "conditional"
                )


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

    if profile.get("AIF-019") == "Yes":
        add(
            "AIF-019",
            "Actions without human approval need further review "
            "of workflow and safeguards.",
            "review"
        )

    if profile.get("AIF-017") in ("No", "Partly"):
        add(
            "AIF-017",
            "Independent assessment of the output may be limited; "
            "review the clinical role.",
            "review"
        )

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


# MAIN STREAMLIT APPLICATION
# ============================================================

def main():
    # Must be the first Streamlit UI command in this script.
    st.set_page_config(
        page_title="AI Regulatory Readiness Platform",
        layout="wide"
    )

    # Match D2.1's overall page layout.
    st.caption("IMAGING AI | REGULATORY GUIDANCE")
    st.title("AI Regulatory Readiness Platform")
    st.info(
        "Complete the AI function and clinical workflow questionnaire. "
        "The information collected will support subsequent regulatory "
        "pathway assessment."
    )

    # Questionnaire is defined in ai_function.py (do not duplicate questions).
    profile = render_ai_function()

    # PROFILE PREVIEW
    # ========================================================

    st.divider()

    if st.button("Preview AI Function Profile", type="primary"):
        issues = validate_ai_function(profile)
        st.session_state["ai_function_profile"] = profile.copy()
        st.session_state["ai_function_validation_issues"] = issues

    # Persist preview across Streamlit reruns, as in D2.1.
    if "ai_function_profile" not in st.session_state:
        return

    saved_profile = st.session_state["ai_function_profile"]
    issues = st.session_state["ai_function_validation_issues"]

    # VALIDATION RESULTS
    # ========================================================
    st.divider()
    st.subheader("AI Function Profile Summary")

    if issues:
        st.warning(f"{len(issues)} questionnaire validation issue(s) identified.")
        st.markdown("### Information Requiring Attention")

        issue_counts = {}
        for issue in issues:
            issue_type = issue["type"]
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        st.markdown("#### Issue Summary")
        for issue_type, count in issue_counts.items():
            st.write(f"**{issue_type.capitalize()}:** {count}")

        st.markdown("#### Detailed Results")
        for issue in issues:
            with st.expander(
                f"{issue['field_id']} — {issue['field']} ({issue['type']})"
            ):
                st.write(f"**Issue:** {issue['issue']}")
                st.write(f"**Type:** {issue['type']}")
                if issue.get("relevant_gates"):
                    st.write(
                        "**Potentially relevant gates:** "
                        + ", ".join(issue["relevant_gates"])
                    )
    else:
        st.success("No questionnaire validation issues identified.")

    # USER-FRIENDLY PROFILE SUMMARY
    # ========================================================
    st.markdown("### AI Function Information")

    for field_id, response in saved_profile.items():
        # Follow-up keys such as AIF-005-DETAILS get a readable label.
        label = FIELD_LABELS.get(field_id)
        if label is None:
            parent_id = field_id.rsplit("-", 1)[0]
            parent_label = FIELD_LABELS.get(parent_id, parent_id)
            suffix = "Other details" if field_id.endswith("-OTHER") else "Details"
            label = f"{parent_label} — {suffix}"

        if is_missing(response):
            display_value = "Not provided"
        elif isinstance(response, list):
            display_value = ", ".join(response)
        else:
            display_value = response

        st.write(f"**{label}:** {display_value}")

    st.caption(
        "This is a preliminary questionnaire information check only. "
        "No regulatory classification or readiness determination has been performed."
    )

    # JSON EXPORT
    # ========================================================
    # Match the D2.1 top-level JSON keys: profile and validation.
    # 'manual_review_required' is reserved for explicit review flags,
    # rather than treating every missing answer as a regulatory review.
    export_data = {
        "profile": saved_profile,
        "validation": {
            "manual_review_required": any(
                issue["type"] == "review" for issue in issues
            ),
            "issues": issues,
        },
    }

    json_data = json.dumps(export_data, indent=4, ensure_ascii=False)

    st.download_button(
        label="Download AI Function Profile",
        data=json_data,
        file_name="ai_function_profile.json",
        mime="application/json",
    )


# Streamlit runs this script directly; importing validate_ai_function
# from another module will not automatically render the questionnaire.
if __name__ == "__main__":
    main()
