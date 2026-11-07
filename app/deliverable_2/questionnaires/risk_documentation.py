import streamlit as st


# ============================================================
# DELIVERABLE 2.5: RISK, CYBERSECURITY, AND DOCUMENTATION
# ============================================================

FIELD_LABELS = {
    "RCD-001": "Risk Management Process",
    "RCD-002": "Identified Product-Related Risks",
    "RCD-003": "Foreseeable Misuse",
    "RCD-004": "Potential Harm",
    "RCD-005": "Risk Severity",
    "RCD-006": "Risk Likelihood",
    "RCD-007": "Risk Control Measures",
    "RCD-008": "Residual Risks",
    "RCD-009": "Benefit-Risk Assessment",
    "CYB-001": "Cybersecurity Risk Assessment",
    "CYB-002": "Data and Information Handled",
    "CYB-003": "Network Connectivity",
    "CYB-004": "Access Control and Authentication",
    "CYB-005": "Data Protection",
    "CYB-006": "Software Updates and Vulnerability Management",
    "CYB-007": "Cybersecurity Incident Response",
    "CYB-008": "Cybersecurity Testing and Evidence",
    "UID-001": "Instructions for Use",
    "UID-002": "Warnings, Precautions, and Limitations",
    "UID-003": "User Training and Supporting Materials",
    "DOC-001": "Technical Documentation",
    "DOC-002": "Risk Management Documentation",
    "DOC-003": "Cybersecurity Documentation",
    "DOC-004": "Regulatory Status and Existing Authorizations",
    "DOC-005": "Supporting Document References",
}


def render_risk_documentation():
    """Display the Deliverable 2.5 questionnaire."""

    st.header("Risk, Cybersecurity, and Documentation Profile")

    st.write(
        "Provide information about product-related risks, risk controls, "
        "cybersecurity measures, user information, and existing regulatory "
        "documentation. Enter Unknown when information has not been determined."
    )

    profile = {}

    # ========================================================
    # SECTION 1: RISK IDENTIFICATION
    # ========================================================

    st.divider()
    st.subheader("01 / Risk Identification")

    profile["RCD-001"] = st.selectbox(
        "Is a documented risk-management process established?",
        ["Select an option", "Yes", "No", "In progress", "Unknown"],
    )

    profile["RCD-002"] = st.text_area(
        "Identify known or anticipated product-related risks or hazards."
    )

    profile["RCD-003"] = st.text_area(
        "Describe foreseeable misuse or reasonably foreseeable use errors."
    )

    profile["RCD-004"] = st.text_area(
        "What potential harm could result from the identified risks?"
    )

    profile["RCD-005"] = st.selectbox(
        "What severity categories or scale are used?",
        [
            "Select an option",
            "Negligible / Minor / Serious / Critical",
            "Numerical scale",
            "Other defined scale",
            "Not established",
            "Unknown",
        ],
    )

    if profile["RCD-005"] in ["Numerical scale", "Other defined scale"]:
        profile["RCD-005-DETAILS"] = st.text_input(
            "Specify the severity scale and its definitions."
        )

    profile["RCD-006"] = st.selectbox(
        "How is likelihood or probability of risk occurrence assessed?",
        [
            "Select an option",
            "Qualitative categories",
            "Numerical probability",
            "Other defined method",
            "Not assessed",
            "Unknown",
        ],
    )

    if profile["RCD-006"] in [
        "Qualitative categories",
        "Numerical probability",
        "Other defined method",
    ]:
        profile["RCD-006-DETAILS"] = st.text_area(
            "Describe the likelihood assessment method."
        )

    # ========================================================
    # SECTION 2: RISK CONTROLS
    # ========================================================

    st.divider()
    st.subheader("02 / Risk Controls and Residual Risk")

    profile["RCD-007"] = st.text_area(
        "Describe the risk-control measures implemented or planned."
    )

    profile["RCD-008"] = st.text_area(
        "Identify residual risks that remain after controls are applied."
    )

    profile["RCD-009"] = st.text_area(
        "Is there a documented benefit-risk assessment? "
        "Summarize its conclusion and supporting evidence."
    )

    # ========================================================
    # SECTION 3: CYBERSECURITY
    # ========================================================

    st.divider()
    st.subheader("03 / Cybersecurity")

    profile["CYB-001"] = st.selectbox(
        "Has a cybersecurity risk assessment been performed?",
        ["Select an option", "Yes", "No", "In progress", "Unknown"],
    )

    profile["CYB-002"] = st.multiselect(
        "What types of data or information does the product handle?",
        [
            "Medical images",
            "Patient-identifiable information",
            "Clinical reports or measurements",
            "User/account information",
            "Device or system logs",
            "Other",
            "Unknown",
        ],
    )

    if "Other" in profile["CYB-002"]:
        profile["CYB-002-OTHER"] = st.text_input(
            "Specify other data or information."
        )

    profile["CYB-003"] = st.selectbox(
        "Does the product connect to a network, cloud service, "
        "or external system?",
        ["Select an option", "Yes", "No", "Unknown"],
    )

    profile["CYB-004"] = st.text_area(
        "Describe access-control and authentication measures."
    )

    profile["CYB-005"] = st.text_area(
        "Describe how product data are protected during storage, "
        "processing, and transmission."
    )

    profile["CYB-006"] = st.text_area(
        "Describe software updates, patching, and vulnerability management."
    )

    profile["CYB-007"] = st.text_area(
        "Describe the cybersecurity incident response process."
    )

    profile["CYB-008"] = st.text_area(
        "List available cybersecurity testing, assessments, "
        "or supporting evidence."
    )

    # ========================================================
    # SECTION 4: USER INFORMATION
    # ========================================================

    st.divider()
    st.subheader("04 / User Information and Documentation")

    profile["UID-001"] = st.selectbox(
        "Are instructions for use or equivalent user instructions available?",
        ["Select an option", "Yes", "No", "In progress", "Unknown"],
    )

    profile["UID-002"] = st.text_area(
        "Describe warnings, precautions, contraindications, "
        "and product limitations communicated to users."
    )

    profile["UID-003"] = st.text_area(
        "Describe user training, onboarding, and supporting materials."
    )

    # ========================================================
    # SECTION 5: REGULATORY DOCUMENTATION
    # ========================================================

    st.divider()
    st.subheader("05 / Regulatory Documentation and Evidence")

    profile["DOC-001"] = st.selectbox(
        "Is product technical documentation available?",
        ["Select an option", "Yes", "No", "In progress", "Unknown"],
    )

    profile["DOC-002"] = st.selectbox(
        "Is risk-management documentation available?",
        ["Select an option", "Yes", "No", "In progress", "Unknown"],
    )

    profile["DOC-003"] = st.selectbox(
        "Is cybersecurity documentation available?",
        ["Select an option", "Yes", "No", "In progress", "Unknown"],
    )

    profile["DOC-004"] = st.selectbox(
        "What is the current regulatory status of the product?",
        [
            "Select an option",
            "Not submitted",
            "Submission in progress",
            "Authorized / cleared / approved in at least one jurisdiction",
            "Not applicable / not determined",
            "Unknown",
        ],
    )

    if profile["DOC-004"] == (
        "Authorized / cleared / approved in at least one jurisdiction"
    ):
        profile["DOC-004-DETAILS"] = st.text_area(
            "Identify the jurisdiction, authorization reference, "
            "product version, and status."
        )

    profile["DOC-005"] = st.text_area(
        "List supporting document names, identifiers, versions, dates, "
        "and page or section references."
    )

    return profile