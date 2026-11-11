import streamlit as st

# ============================================================
# QUESTIONNAIRE IMPORTS
# ============================================================

from app.deliverable_2.questionnaires.product_profile import (
    render_product_profile,
)

from app.deliverable_2.questionnaires.ai_function import (
    render_ai_function,
)

from app.deliverable_2.questionnaires.Dataset_and_evidence import (
    render_dataset_evidence,
)

from app.deliverable_2.questionnaires.risk_documentation import (
    render_risk_documentation,
)


# ============================================================
# VALIDATION IMPORTS
# ============================================================

from app.deliverable_3.product_validation import (
    validate_profile,
)

from app.deliverable_2.validation.run_ai_function import (
    validate_ai_function,
)

from app.deliverable_3.dataset_validation import (
    validate_dataset_evidence,
)

from app.deliverable_3.risk_validation import (
    validate_risk_documentation,
)

from app.deliverable_3.validation_summary import (
    build_validation_summary,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Regulatory Readiness Platform",
    layout="wide",
)

st.caption("IMAGING AI | REGULATORY GUIDANCE")

st.title("AI Regulatory Readiness Platform")

st.info(
    "This platform collects information about imaging AI "
    "technologies to support preliminary regulatory assessment. "
    "It does not replace professional regulatory review."
)


# ============================================================
# QUESTIONNAIRES
# ============================================================

st.subheader("Part 1: Product and Intended-Use Profile")

product_profile = render_product_profile()

st.divider()

st.subheader("Part 2: AI Function and Clinical Workflow")

ai_function_profile = render_ai_function()

st.divider()

st.subheader("Part 3: Dataset and Evidence Profile")

dataset_profile = render_dataset_evidence()

st.divider()

st.subheader("Part 4: Risk, Cybersecurity, and Documentation")

risk_profile = render_risk_documentation()


# ============================================================
# VALIDATION BUTTON
# ============================================================

st.divider()

st.header("Questionnaire Validation")

st.write(
    "Validate the collected information to identify missing "
    "responses, conditional requirements, uncertainties, "
    "and potential inconsistencies."
)

if st.button("Validate Questionnaires", type="primary"):

    product_issues = validate_profile(product_profile)

    ai_function_issues = validate_ai_function(
        ai_function_profile
    )

    dataset_issues = validate_dataset_evidence(
        dataset_profile
    )

    risk_issues = validate_risk_documentation(
        risk_profile
    )

    # Store collected questionnaire responses
    st.session_state["integrated_profiles"] = {
        "product_profile": product_profile,
        "ai_function": ai_function_profile,
        "dataset_evidence": dataset_profile,
        "risk_documentation": risk_profile,
    }

    # Store validation issues from each questionnaire
    st.session_state["integrated_validation"] = {
        "product_profile": product_issues,
        "ai_function": ai_function_issues,
        "dataset_evidence": dataset_issues,
        "risk_documentation": risk_issues,
    }


# ============================================================
# DISPLAY VALIDATION RESULTS
# ============================================================

if "integrated_validation" in st.session_state:

    validation = st.session_state["integrated_validation"]

    st.divider()

    st.header("Validation Results")

    sections = [
        (
            "Part 1: Product Profile Validation",
            "product_profile",
        ),
        (
            "Part 2: AI Function Validation",
            "ai_function",
        ),
        (
            "Part 3: Dataset and Evidence Validation",
            "dataset_evidence",
        ),
        (
            "Part 4: Risk, Cybersecurity, and Documentation Validation",
            "risk_documentation",
        ),
    ]

    for section_title, section_key in sections:

        st.subheader(section_title)

        issues = validation.get(section_key, [])

        missing_count = sum(
            issue.get("type") == "missing"
            for issue in issues
        )

        conditional_count = sum(
            issue.get("type") == "conditional"
            for issue in issues
        )

        uncertain_count = sum(
            issue.get("type") == "uncertain"
            for issue in issues
        )

        review_count = sum(
            issue.get("type") == "review"
            for issue in issues
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Missing", missing_count)

        col2.metric("Conditional", conditional_count)

        col3.metric("Uncertain", uncertain_count)

        col4.metric("Total Issues", len(issues))

        if issues:

            st.warning(
                "This questionnaire contains information "
                "that requires attention."
            )

            with st.expander(
                f"View {len(issues)} validation issues",
                expanded=True,
            ):

                for issue in issues:

                    field_name = issue.get(
                        "field",
                        issue.get("field_id", "Unknown field"),
                    )

                    field_id = issue.get(
                        "field_id",
                        "Unknown",
                    )

                    message = issue.get(
                        "issue",
                        "Information requires attention.",
                    )

                    issue_type = issue.get(
                        "type",
                        "unspecified",
                    )

                    st.markdown(
                        f"**{field_name} ({field_id})**"
                    )

                    st.write(message)

                    st.caption(
                        f"Issue type: {issue_type}"
                    )

                    if issue.get("record"):

                        st.caption(
                            f"Record: {issue['record']}"
                        )

                    gates = issue.get(
                        "relevant_gates",
                        [],
                    )

                    if gates:

                        st.caption(
                            "Relevant readiness gates: "
                            + ", ".join(gates)
                        )

                    st.divider()

        else:

            st.success(
                "No validation issues were identified "
                "by the current rules."
            )


    # ========================================================
    # OVERALL VALIDATION SUMMARY
    # ========================================================

    st.divider()

    st.header("Overall Validation Summary")

    # Generate standardized validation summary
    summary = build_validation_summary(validation)

    # Store summary for future regulatory guidance integration
    st.session_state["validation_summary"] = summary

    # Display consolidated results
    st.json(summary)


    # ========================================================
    # COLLECTED QUESTIONNAIRE RESPONSES
    # ========================================================

    st.divider()

    st.header("Collected Questionnaire Responses")

    profiles = st.session_state["integrated_profiles"]

    with st.expander("D2.1: Product Profile"):
        st.json(profiles["product_profile"])

    with st.expander("D2.2: AI Function"):
        st.json(profiles["ai_function"])

    with st.expander("D2.4: Dataset and Evidence"):
        st.json(profiles["dataset_evidence"])

    with st.expander(
        "D2.5: Risk, Cybersecurity, and Documentation"
    ):
        st.json(profiles["risk_documentation"])

    st.caption(
        "These results represent preliminary information-quality "
        "checks only. They do not establish regulatory classification, "
        "compliance, approval, or overall regulatory readiness. "
        "Explicit manual-review flags are distinguished from "
        "missing information, conditional requirements, and "
        "unresolved uncertainties."
    )