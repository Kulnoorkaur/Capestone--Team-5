import json
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
# RAG AND LLM IMPORTS
# ============================================================

from app.rag.rag_pipeline import (
    generate_regulatory_response,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Regulatory Readiness Platform",
    layout="wide",
)


# ============================================================
# APPLICATION HEADER
# ============================================================

st.caption("IMAGING AI | REGULATORY GUIDANCE")

st.title("AI Regulatory Readiness Platform")

st.info(
    "This platform collects information about imaging AI "
    "technologies to support preliminary regulatory assessment. "
    "It does not replace professional regulatory review."
)


# ============================================================
# PART 1: PRODUCT AND INTENDED-USE PROFILE
# ============================================================

st.header("Product Information")

st.subheader("Part 1: Product and Intended-Use Profile")

product_profile = render_product_profile()

st.divider()


# ============================================================
# PART 2: AI FUNCTION AND CLINICAL WORKFLOW
# ============================================================

st.subheader("Part 2: AI Function and Clinical Workflow")

ai_function_profile = render_ai_function()

st.divider()


# ============================================================
# PART 3: DATASET AND EVIDENCE PROFILE
# ============================================================

st.subheader("Part 3: Dataset and Evidence Profile")

dataset_profile = render_dataset_evidence()

st.divider()


# ============================================================
# PART 4: RISK, CYBERSECURITY, AND DOCUMENTATION
# ============================================================

st.subheader(
    "Part 4: Risk, Cybersecurity, and Documentation"
)

risk_profile = render_risk_documentation()


# ============================================================
# QUESTIONNAIRE VALIDATION
# ============================================================

st.divider()

st.header("Questionnaire Validation")

st.write(
    "Validate the collected information to identify missing "
    "responses, conditional requirements, uncertainties, "
    "and potential inconsistencies."
)


if st.button(
    "Validate Questionnaires",
    type="primary",
):

    # --------------------------------------------------------
    # VALIDATE INDIVIDUAL QUESTIONNAIRES
    # --------------------------------------------------------

    product_issues = validate_profile(
        product_profile
    )

    ai_function_issues = validate_ai_function(
        ai_function_profile
    )

    dataset_issues = validate_dataset_evidence(
        dataset_profile
    )

    risk_issues = validate_risk_documentation(
        risk_profile
    )

    # --------------------------------------------------------
    # STORE QUESTIONNAIRE RESPONSES
    # --------------------------------------------------------

    st.session_state["integrated_profiles"] = {
        "product_profile": product_profile,
        "ai_function": ai_function_profile,
        "dataset_evidence": dataset_profile,
        "risk_documentation": risk_profile,
    }

    # --------------------------------------------------------
    # STORE VALIDATION RESULTS
    # --------------------------------------------------------

    st.session_state["integrated_validation"] = {
        "product_profile": product_issues,
        "ai_function": ai_function_issues,
        "dataset_evidence": dataset_issues,
        "risk_documentation": risk_issues,
    }

    # Clear previous assessment when profiles are revalidated.
    st.session_state.pop(
        "regulatory_assessment",
        None
    )


# ============================================================
# DISPLAY VALIDATION RESULTS
# ============================================================

if "integrated_validation" in st.session_state:

    validation = st.session_state[
        "integrated_validation"
    ]

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

    # --------------------------------------------------------
    # INDIVIDUAL VALIDATION SUMMARIES
    # --------------------------------------------------------

    for section_title, section_key in sections:

        st.subheader(section_title)

        issues = validation.get(
            section_key,
            []
        )

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

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Missing",
            missing_count
        )

        col2.metric(
            "Conditional",
            conditional_count
        )

        col3.metric(
            "Uncertain",
            uncertain_count
        )

        col4.metric(
            "Total Issues",
            len(issues)
        )

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
                        issue.get(
                            "field_id",
                            "Unknown field"
                        ),
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

    summary = build_validation_summary(
        validation
    )

    st.session_state["validation_summary"] = summary

    st.json(summary)


    # ========================================================
    # COLLECTED QUESTIONNAIRE RESPONSES
    # ========================================================

    st.divider()

    st.header("Collected Questionnaire Responses")

    profiles = st.session_state[
        "integrated_profiles"
    ]

    with st.expander("D2.1: Product Profile"):

        st.json(
            profiles["product_profile"]
        )

    with st.expander("D2.2: AI Function"):

        st.json(
            profiles["ai_function"]
        )

    with st.expander("D2.4: Dataset and Evidence"):

        st.json(
            profiles["dataset_evidence"]
        )

    with st.expander(
        "D2.5: Risk, Cybersecurity, and Documentation"
    ):

        st.json(
            profiles["risk_documentation"]
        )

    st.caption(
        "These results represent preliminary information-quality "
        "checks only. They do not establish regulatory classification, "
        "compliance, approval, or overall regulatory readiness. "
        "Explicit manual-review flags are distinguished from "
        "missing information, conditional requirements, and "
        "unresolved uncertainties."
    )


# ============================================================
# AI-POWERED REGULATORY ASSESSMENT
# ============================================================

st.divider()

st.header("AI-Powered Regulatory Assessment")

st.write(
    "Generate preliminary regulatory guidance using the "
    "information collected through the questionnaires and "
    "retrieved regulatory research."
)


# ============================================================
# JURISDICTION SELECTION
# ============================================================

jurisdiction = st.selectbox(
    "Select Regulatory Jurisdiction",
    [
        "Canada",
        "USA",
    ],
    key="regulatory_jurisdiction",
)


# ============================================================
# GENERATE REGULATORY ASSESSMENT
# ============================================================

if st.button(
    "Generate Regulatory Assessment",
    type="primary",
):

    if "integrated_profiles" not in st.session_state:

        st.error(
            "Please validate the questionnaires before "
            "generating a regulatory assessment."
        )

    else:

        profiles = st.session_state[
            "integrated_profiles"
        ]

        summary = st.session_state.get(
            "validation_summary",
            {}
        )

        # ----------------------------------------------------
        # COMBINE QUESTIONNAIRE INFORMATION
        # ----------------------------------------------------

        assessment_context = {

            "jurisdiction": jurisdiction,

            "product_profile": profiles[
                "product_profile"
            ],

            "ai_function": profiles[
                "ai_function"
            ],

            "dataset_evidence": profiles[
                "dataset_evidence"
            ],

            "risk_documentation": profiles[
                "risk_documentation"
            ],

            "validation_summary": summary,

        }

        # ----------------------------------------------------
        # CONSTRUCT REGULATORY ASSESSMENT QUESTION
        # ----------------------------------------------------

        regulatory_question = f"""

You are conducting a preliminary regulatory readiness
assessment for an AI-enabled medical imaging product.

SELECTED JURISDICTION:

{jurisdiction}

PRODUCT AND QUESTIONNAIRE INFORMATION:

{json.dumps(
    assessment_context,
    indent=2,
    ensure_ascii=False
)}

ASSESSMENT REQUIREMENTS:

1. Evaluate the product's intended medical purpose
   and clinical application.

2. Identify potential regulatory scope and
   classification considerations.

3. Evaluate the AI functionality and its role
   within clinical workflows.

4. Assess relevant dataset, validation, and
   clinical evidence considerations.

5. Evaluate identified product-related risks
   and cybersecurity documentation.

6. Identify missing information, conditional
   requirements, and unresolved uncertainties.

7. Distinguish established product information
   from assumptions.

8. Identify relevant regulatory evidence
   and supporting sources.

9. Recommend appropriate regulatory
   readiness next steps.

10. Do not invent missing product information.

11. Do not provide definitive regulatory
    classifications without sufficient evidence.

12. Do not interpret missing information
    as evidence of compliance.

13. Explain where additional documentation
    or professional review is necessary.

14. Only apply the regulatory framework
    relevant to the selected jurisdiction.

Provide a structured preliminary regulatory
readiness assessment.

Clearly distinguish regulatory requirements,
guidance, recommendations, and uncertainties.

"""

        # ----------------------------------------------------
        # GENERATE RESPONSE USING RAG AND GEMINI
        # ----------------------------------------------------

        with st.spinner(
            "Retrieving regulatory evidence and generating assessment..."
        ):

            try:

                result = generate_regulatory_response(
                    question=regulatory_question,
                    jurisdiction=jurisdiction,
                    top_k=5,
                )

                st.session_state[
                    "regulatory_assessment"
                ] = result

            except Exception as error:

                st.error(
                    "Unable to generate regulatory assessment. "
                    "Please check the RAG pipeline, Gemini "
                    "connection, and regulatory documents."
                )

                st.exception(error)


# ============================================================
# DISPLAY REGULATORY ASSESSMENT
# ============================================================

if "regulatory_assessment" in st.session_state:

    result = st.session_state[
        "regulatory_assessment"
    ]

    st.divider()

    st.header("Preliminary Regulatory Assessment")

    # --------------------------------------------------------
    # GENERATED GEMINI RESPONSE
    # --------------------------------------------------------

    st.markdown(
        result["answer"]
    )

    # --------------------------------------------------------
    # RETRIEVED REGULATORY SOURCES
    # --------------------------------------------------------

    st.divider()

    st.subheader("Retrieved Regulatory Evidence")

    if result["sources"]:

        for source in result["sources"]:

            with st.expander(
                f"{source['source']} — Chunk {source['chunk_id']}"
            ):

                st.write(
                    "**Jurisdiction:**",
                    source["jurisdiction"]
                )

                st.write(
                    "**Similarity Score:**",
                    source["similarity_score"]
                )

    else:

        st.warning(
            "No supporting regulatory documents were retrieved. "
            "A substantive regulatory assessment should not "
            "be relied upon."
        )

    # --------------------------------------------------------
    # CITATION VALIDATION
    # --------------------------------------------------------

    st.divider()

    st.subheader("Citation Validation")

    citation_results = result[
        "citation_validation"
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Citations",
        citation_results["total_citations"]
    )

    col2.metric(
        "Valid Citations",
        citation_results["valid_citations"]
    )

    col3.metric(
        "Invalid Citations",
        len(
            citation_results["invalid_citations"]
        )
    )

    if citation_results["all_citations_valid"]:

        st.success(
            "All citation identifiers match the retrieved evidence."
        )

    else:

        st.warning(
            "Some citations could not be matched to retrieved evidence."
        )

        st.json(
            citation_results["invalid_citations"]
        )

    # --------------------------------------------------------
    # FINAL DISCLAIMER
    # --------------------------------------------------------

    st.caption(
        "Citation validation confirms source and chunk identifiers. "
        "It does not independently establish that cited evidence "
        "supports every associated claim. This assessment is "
        "preliminary and does not constitute regulatory approval, "
        "compliance determination, or legal advice. All conclusions "
        "require verification against current official regulatory "
        "requirements and guidance."
    )