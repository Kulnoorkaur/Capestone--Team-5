import streamlit as st


# ============================================================
# DELIVERABLE 2.1: PRODUCT AND INTENDED-USE PROFILE
# ============================================================

# Internal identifiers and user-facing labels

FIELD_LABELS = {
    "PIP-001": "Product Name and Version",
    "PIP-002": "Intended Medical Purpose",
    "PIP-003": "Clinical Problem",
    "PIP-004": "Clinical Application",
    "PIP-005": "Anatomical Region",
    "PIP-006": "Imaging Modality",
    "PIP-007": "Intended User Roles",
    "PIP-008": "Professional or Patient Use",
    "PIP-009": "Specialized Training Required",
    "PIP-010": "Required User Qualifications",
    "PIP-011": "Intended Patient Age Range",
    "PIP-012": "Target Patient Population",
    "PIP-013": "Excluded Patient Populations",
    "PIP-014": "Patient Population Restrictions",
    "PIP-015": "Clinical Eligibility Criteria",
    "PIP-016": "Intended Clinical Setting",
    "PIP-017": "Care Context",
    "PIP-018": "Routine or Time-Critical Use",
    "PIP-019": "Clinical Pathway Stage",
    "PIP-020": "Principal Product Functions",
    "PIP-021": "Imaging Information Processed",
    "PIP-022": "Product Operations",
    "PIP-023": "Intended Clinical Use of Results",
    "PIP-024": "Excluded Uses and Limitations"
}


def render_product_profile():
    """
    Renders the Deliverable 2.1 questionnaire.

    PIP identifiers are stored internally and are not
    displayed in the user-facing interface.
    """

    st.header("Product and Intended-Use Profile")

    st.write(
        "Provide information about your imaging AI product "
        "to support a preliminary regulatory assessment."
    )

    profile = {}

    # ========================================================
    # SECTION 1: PRODUCT IDENTIFICATION
    # ========================================================

    st.divider()
    st.subheader("01 / Product Identification")

    profile["PIP-001"] = st.text_input(
        "Product Name and Version",
        placeholder="Example: LungScan AI, Version 1.0",
        key="PIP-001"
    )

    profile["PIP-002"] = st.text_area(
        "Intended Medical Purpose",
        placeholder=(
            "Describe whether the product is intended for "
            "diagnosis, monitoring, prediction, or treatment support."
        ),
        height=100,
        key="PIP-002"
    )

    profile["PIP-003"] = st.text_area(
        "Clinical Problem",
        placeholder=(
            "What clinical problem or medical condition "
            "is the product intended to address?"
        ),
        height=100,
        key="PIP-003"
    )

    profile["PIP-004"] = st.text_area(
        "Clinical Application",
        placeholder=(
            "Describe how the product will be used "
            "within clinical practice."
        ),
        height=100,
        key="PIP-004"
    )

    profile["PIP-005"] = st.text_input(
        "Anatomical Region",
        placeholder="Example: Lungs, brain, breast",
        key="PIP-005"
    )

    profile["PIP-006"] = st.selectbox(
        "Imaging Modality",
        [
            "Select an option",
            "CT",
            "MRI",
            "X-ray",
            "Ultrasound",
            "PET",
            "Other"
        ],
        key="PIP-006"
    )

    if profile["PIP-006"] == "Other":
        profile["PIP-006-OTHER"] = st.text_input(
            "Please specify the imaging modality",
            key="PIP-006-OTHER"
        )

    # ========================================================
    # SECTION 2: INTENDED USERS
    # ========================================================

    st.divider()
    st.subheader("02 / Intended Users")

    profile["PIP-007"] = st.multiselect(
        "Intended User Roles",
        [
            "Radiologist",
            "Physician",
            "Technologist",
            "Nurse",
            "Other healthcare professional",
            "Patient",
            "Caregiver",
            "Other"
        ],
        key="PIP-007"
    )

    if "Other" in profile["PIP-007"]:
        profile["PIP-007-OTHER"] = st.text_input(
            "Please specify the intended user role",
            key="PIP-007-OTHER"
        )

    profile["PIP-008"] = st.selectbox(
        "Professional or Patient Use",
        [
            "Select an option",
            "Healthcare professional only",
            "Patient or caregiver",
            "Both"
        ],
        key="PIP-008"
    )

    profile["PIP-009"] = st.selectbox(
        "Specialized Training Required",
        [
            "Select an option",
            "Yes",
            "No",
            "Unknown"
        ],
        key="PIP-009"
    )

    # Professional qualifications are relevant even when
    # additional product-specific training is not required.

    profile["PIP-010"] = st.text_area(
        "Required User Qualifications",
        placeholder=(
            "Describe professional qualifications and any "
            "product-specific training requirements. "
            "If none apply, enter 'None'."
        ),
        height=100,
        key="PIP-010"
    )

    if profile["PIP-009"] == "Yes":
        profile["TRAINING-DETAILS"] = st.text_area(
            "Describe the specialized training required",
            placeholder=(
                "Explain what training users must complete "
                "before operating the product."
            ),
            height=100,
            key="TRAINING-DETAILS"
        )

    elif profile["PIP-009"] == "Unknown":
        st.warning(
            "Specialized training requirements are unknown. "
            "This information will be flagged for manual review."
        )

    # ========================================================
    # SECTION 3: PATIENT POPULATION
    # ========================================================

    st.divider()
    st.subheader("03 / Patient Population")

    profile["PIP-011"] = st.text_input(
        "Intended Patient Age Range",
        placeholder="Example: Adults aged 18 years and older",
        key="PIP-011"
    )

    profile["PIP-012"] = st.text_area(
        "Target Patient Population",
        placeholder=(
            "Describe the patient population for whom "
            "the product is intended."
        ),
        height=100,
        key="PIP-012"
    )

    profile["PIP-013"] = st.text_area(
        "Excluded Patient Populations",
        placeholder=(
            "Identify excluded patient groups. "
            "If there are no exclusions, enter 'None'."
        ),
        height=100,
        key="PIP-013"
    )

    profile["PIP-014"] = st.text_area(
        "Patient Population Restrictions",
        placeholder=(
            "Describe restrictions related to age, "
            "clinical condition, or other characteristics."
        ),
        height=100,
        key="PIP-014"
    )

    profile["PIP-015"] = st.text_area(
        "Clinical Eligibility Criteria",
        placeholder=(
            "Describe the criteria that determine "
            "whether a patient is eligible for use."
        ),
        height=100,
        key="PIP-015"
    )

    # ========================================================
    # SECTION 4: CLINICAL SETTING
    # ========================================================

    st.divider()
    st.subheader("04 / Clinical Setting")

    profile["PIP-016"] = st.multiselect(
        "Intended Clinical Setting",
        [
            "Hospital",
            "Outpatient clinic",
            "Diagnostic imaging centre",
            "Emergency department",
            "Home",
            "Other"
        ],
        key="PIP-016"
    )

    if "Other" in profile["PIP-016"]:
        profile["PIP-016-OTHER"] = st.text_input(
            "Please specify the clinical setting",
            key="PIP-016-OTHER"
        )

    profile["PIP-017"] = st.selectbox(
        "Care Context",
        [
            "Select an option",
            "Screening",
            "Diagnosis",
            "Monitoring",
            "Treatment planning",
            "Follow-up",
            "Other"
        ],
        key="PIP-017"
    )

    if profile["PIP-017"] == "Other":
        profile["PIP-017-OTHER"] = st.text_input(
            "Please specify the care context",
            key="PIP-017-OTHER"
        )

    profile["PIP-018"] = st.selectbox(
        "Routine or Time-Critical Use",
        [
            "Select an option",
            "Routine",
            "Time-critical",
            "Both",
            "Unknown"
        ],
        key="PIP-018"
    )

    profile["PIP-019"] = st.text_area(
        "Clinical Pathway Stage",
        placeholder=(
            "At what stage of the clinical workflow "
            "will the product be used?"
        ),
        height=100,
        key="PIP-019"
    )

    # ========================================================
    # SECTION 5: PRODUCT FUNCTIONS AND LIMITATIONS
    # ========================================================

    st.divider()
    st.subheader("05 / Product Functions and Limitations")

    profile["PIP-020"] = st.text_area(
        "Principal Product Functions",
        placeholder=(
            "Describe the main functions performed "
            "by the imaging AI product."
        ),
        height=100,
        key="PIP-020"
    )

    profile["PIP-021"] = st.text_area(
        "Imaging Information Processed",
        placeholder=(
            "Describe the types of images or imaging "
            "information processed by the product."
        ),
        height=100,
        key="PIP-021"
    )

    profile["PIP-022"] = st.multiselect(
        "Product Operations",
        [
            "Image analysis",
            "Detection",
            "Classification",
            "Segmentation",
            "Quantification",
            "Prediction",
            "Other"
        ],
        key="PIP-022"
    )

    if "Other" in profile["PIP-022"]:
        profile["PIP-022-OTHER"] = st.text_input(
            "Please specify the product operation",
            key="PIP-022-OTHER"
        )

    profile["PIP-023"] = st.text_area(
        "Intended Clinical Use of Results",
        placeholder=(
            "Explain how healthcare professionals "
            "or other intended users will use the results."
        ),
        height=100,
        key="PIP-023"
    )

    profile["PIP-024"] = st.text_area(
        "Excluded Uses and Limitations",
        placeholder=(
            "Describe uses that are not intended "
            "or known limitations of the product."
        ),
        height=100,
        key="PIP-024"
    )

    return profile
