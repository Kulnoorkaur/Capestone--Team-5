"""D2.2 AI Function and Clinical Workflow questionnaire (Streamlit)."""

import streamlit as st

# QUESTION LABELS

FIELD_LABELS = {
    "AIF-001": "AI Input Information",
    "AIF-002": "Technical Input Requirements and Limitations",
    "AIF-003": "Input Sources and Transfer",
    "AIF-004": "AI Input Processing",
    "AIF-005": "Image Modification or Generation",
    "AIF-006": "AI Outputs",
    "AIF-007": "Output Presentation and Delivery",
    "AIF-008": "Clinical Meaning of Outputs",
    "AIF-009": "Output Interpretation Information",
    "AIF-010": "Intended Clinical Use of AI Outputs",
    "AIF-011": "Output Recipient and Decision Responsibility",
    "AIF-012": "Subsequent Clinical Actions",
    "AIF-013": "Consequences of Incorrect or Missing Outputs",
    "AIF-014": "Additional Clinical Confirmation",
    "AIF-015": "Automatically Initiated Tasks",
    "AIF-016": "Professional Review Before Clinical Action",
    "AIF-017": "Independent Assessment of AI Output",
    "AIF-018": "User Control Over AI Output or Action",
    "AIF-019": "Actions Initiated Without Human Approval",
    "AIF-020": "Handling Inadequate or Uncertain Inputs",
}

CHOICES_YNU = ["Select an option", "Yes", "No", "Unknown"]

# OTHER OPTION FOLLOW-UP

def _other_details(profile, field_id, multiple=False):
    """Show an extra text box when the user selects Other."""

    value = profile[field_id]

    selected = "Other" in value if multiple else value == "Other"

    if selected:
        profile[f"{field_id}-OTHER"] = st.text_input(
            "Please specify the other option",
            key=f"{field_id}-OTHER",
        )


# QUESTIONNAIRE
# ============================================================

def render_ai_function():
    """Display the questionnaire and collect responses."""

    st.header("AI Function and Clinical Workflow")

    st.write(
        "Describe how the imaging-AI software uses inputs, produces outputs, "
        "and interacts with healthcare professionals. This section collects "
        "product information; it does not determine regulatory classification."
    )

    profile = {}

    # SECTION 1: AI INPUTS AND PROCESSING

    st.divider()
    st.subheader("01 / AI Inputs and Processing")

    profile["AIF-001"] = st.multiselect(
        "What input information does the software use?",
        [
            "Medical images",
            "Image-derived measurements",
            "Clinical metadata",
            "Other",
        ],
        key="AIF-001",
    )

    _other_details(profile, "AIF-001", multiple=True)

    profile["AIF-002"] = st.text_area(
        "What technical input requirements or limitations apply?",
        placeholder=(
            "Supported formats, resolution, image quality, and unsupported "
            "conditions; enter 'Unknown' if not established."
        ),
        key="AIF-002",
        height=100,
    )

    profile["AIF-003"] = st.multiselect(
        "Where do inputs come from, and how are they received?",
        [
            "Scanner",
            "PACS",
            "EHR",
            "User upload",
            "Other",
        ],
        key="AIF-003",
    )

    _other_details(profile, "AIF-003", multiple=True)

    profile["AIF-004"] = st.text_area(
        "How does the AI process the input information to perform its function?",
        placeholder=(
            "Describe the processing steps; distinguish this from "
            "the overall product operations in D2.1."
        ),
        key="AIF-004",
        height=100,
    )

    profile["AIF-005"] = st.selectbox(
        "Does the AI alter an image or create a new image for clinical interpretation?",
        CHOICES_YNU,
        key="AIF-005",
    )

    if profile["AIF-005"] == "Yes":
        profile["AIF-005-DETAILS"] = st.text_area(
            "Describe the modification or generated image, and whether the original is retained.",
            key="AIF-005-DETAILS",
            height=100,
        )

    # SECTION 2: AI OUTPUTS AND PRESENTATION

    st.divider()
    st.subheader("02 / AI Outputs and Presentation")

    profile["AIF-006"] = st.multiselect(
        "What does the software output?",
        [
            "Label",
            "Probability",
            "Score",
            "Alert",
            "Measurement",
            "Segmentation",
            "Transformed image",
            "Recommendation",
            "Other",
        ],
        key="AIF-006",
    )

    _other_details(profile, "AIF-006", multiple=True)

    profile["AIF-007"] = st.multiselect(
        "How is the output displayed or delivered?",
        [
            "Image overlay",
            "Report",
            "Dashboard",
            "PACS",
            "EHR",
            "Notification",
            "API",
            "Other",
        ],
        key="AIF-007",
    )

    _other_details(profile, "AIF-007", multiple=True)

    profile["AIF-008"] = st.text_area(
        "What clinical information or finding does the output represent?",
        key="AIF-008",
        height=100,
    )

    profile["AIF-009"] = st.multiselect(
        "What information helps users interpret the output?",
        [
            "Thresholds",
            "Confidence or uncertainty",
            "Explanations",
            "Warnings or limitations",
            "None",
            "Unknown",
            "Other",
        ],
        key="AIF-009",
    )

    _other_details(profile, "AIF-009", multiple=True)

    profile["AIF-010"] = st.text_area(
        "Is the output intended to inform, prioritize, support, or determine a clinical action? Explain.",
        key="AIF-010",
        height=100,
    )

    # SECTION 3: CLINICAL ROLE AND WORKFLOW

    st.divider()
    st.subheader("03 / Clinical Role and Workflow")

    profile["AIF-011"] = st.text_area(
        "Who receives the AI output, and who is responsible for the clinical decision?",
        placeholder="Reference intended user roles from D2.1 where appropriate.",
        key="AIF-011",
        height=100,
    )

    profile["AIF-012"] = st.multiselect(
        "What clinical action or decision may follow the output?",
        [
            "Clinical review",
            "Referral",
            "Additional workup",
            "Treatment",
            "No action",
            "Other",
        ],
        key="AIF-012",
    )

    _other_details(profile, "AIF-012", multiple=True)

    profile["AIF-013"] = st.text_area(
        "What could happen if the AI output is incorrect, delayed, or missing?",
        key="AIF-013",
        height=100,
    )

    profile["AIF-014"] = st.selectbox(
        "Does the AI output require additional clinical confirmation before a decision?",
        [
            "Select an option",
            "Yes",
            "No",
            "Sometimes",
            "Unknown",
        ],
        key="AIF-014",
    )

    if profile["AIF-014"] in ("Yes", "Sometimes"):
        profile["AIF-014-DETAILS"] = st.text_area(
            "Describe what confirmation is required and when it occurs.",
            key="AIF-014-DETAILS",
            height=100,
        )

    # SECTION 4: AUTOMATION AND CLINICIAN INTERACTION

    st.divider()
    st.subheader("04 / Automation and Clinician Interaction")

    profile["AIF-015"] = st.text_area(
        "Which tasks run automatically without user initiation?",
        placeholder=(
            "Describe tasks, triggers, and how they start; "
            "enter 'None' if applicable."
        ),
        key="AIF-015",
        height=100,
    )

    profile["AIF-016"] = st.selectbox(
        "Is the AI output reviewed by a healthcare professional before clinical action?",
        [
            "Select an option",
            "Always",
            "Sometimes",
            "Never",
            "Unknown",
        ],
        key="AIF-016",
    )

    if profile["AIF-016"] in ("Always", "Sometimes", "Never"):
        profile["AIF-016-DETAILS"] = st.text_area(
            "Describe the review and action sequence.",
            key="AIF-016-DETAILS",
            height=100,
        )

    profile["AIF-017"] = st.selectbox(
        "Can healthcare professionals independently assess information supporting the AI output?",
        [
            "Select an option",
            "Yes",
            "Partly",
            "No",
            "Unknown",
        ],
        key="AIF-017",
    )

    if profile["AIF-017"] in ("Yes", "Partly", "No"):
        profile["AIF-017-DETAILS"] = st.text_area(
            "Describe the source information or evidence available for independent assessment.",
            key="AIF-017-DETAILS",
            height=100,
        )

    profile["AIF-018"] = st.multiselect(
        "What control does the intended user have over the AI output or action?",
        [
            "Disregard",
            "Correct",
            "Override",
            "Stop",
            "None",
            "Other",
        ],
        key="AIF-018",
    )

    _other_details(profile, "AIF-018", multiple=True)

    profile["AIF-019"] = st.selectbox(
        "Can the AI initiate a clinical or workflow action without human approval?",
        CHOICES_YNU,
        key="AIF-019",
    )

    if profile["AIF-019"] == "Yes":
        profile["AIF-019-DETAILS"] = st.text_area(
            "Describe the actions, triggers, and safeguards.",
            key="AIF-019-DETAILS",
            height=100,
        )

    profile["AIF-020"] = st.multiselect(
        "How does the system respond to inadequate input quality or uncertain results?",
        [
            "Reject input",
            "Flag issue",
            "Withhold result",
            "Request human review",
            "Unknown",
            "Other",
        ],
        key="AIF-020",
    )

    _other_details(profile, "AIF-020", multiple=True)

    return profile


