import streamlit as st

def show_ai_function_questionnaire():

    st.header("AI Function and Clinical Workflow")

    st.write(
        "This section collects information about the AI system's "
        "inputs, outputs, clinical role, and level of automation."
    )

    st.subheader("2.1 AI Inputs and Processing")

    aif_001 = st.multiselect(
        "AIF-001: What input information does the software use?",
        [
            "Medical images",
            "Image-derived measurements",
            "Clinical metadata",
            "Other"
        ]
    )

    aif_002 = st.text_area(
        "AIF-002: What technical input requirements or limitations "
        "apply to the AI function?"
    )

    aif_003 = st.multiselect(
        "AIF-003: Where do inputs come from and how are they received?",
        [
            "Scanner",
            "PACS",
            "EHR",
            "User upload",
            "Other"
        ]
    )

    aif_004 = st.text_area(
        "AIF-004: Describe how the AI processes the input information "
        "to perform its intended function."
    )

    aif_005 = st.selectbox(
        "AIF-005: Does the AI alter an image or create a new image "
        "for clinical interpretation?",
        ["Select an answer", "Yes", "No", "Unknown"]
    )

    aif_005_details = ""

    if aif_005 == "Yes":
        aif_005_details = st.text_area(
            "Describe the image modification and whether "
            "the original image is retained."
        )

    answers = {
        "AIF-001": aif_001,
        "AIF-002": aif_002,
        "AIF-003": aif_003,
        "AIF-004": aif_004,
        "AIF-005": {
            "value": aif_005,
            "description": aif_005_details
        }
    }

    return answers
