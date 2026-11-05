import streamlit as st
# Deliverable 2.2: AI Function and Clinical Workflow

FIELD_LABELS = {
    "AIF-001": "AI Input Information",
    "AIF-002": "Technical Input Requirements",
    "AIF-003": "Input Sources",
    "AIF-004": "AI Processing",
    "AIF-005": "Image Modification"
}

def render_ai_function():

    st.header("AI Function and Clinical Workflow")

    st.write(
        "Provide information about how the AI system "
        "processes inputs, generates outputs, and "
        "interacts with healthcare professionals."
    )

    profile = {}

    # SECTION 1: AI INPUTS AND PROCESSING
    
    st.divider()
    st.subheader("01 / AI Inputs and Processing")

    profile["AIF-001"] = st.multiselect(
        "AI Input Information",
        [
            "Medical images",
            "Image-derived measurements",
            "Clinical metadata",
            "Other"
        ],
        key="AIF-001"
    )

    if "Other" in profile["AIF-001"]:
        profile["AIF-001-OTHER"] = st.text_input(
            "Please specify the other input information",
            key="AIF-001-OTHER"
        )

    profile["AIF-002"] = st.text_area(
        "Technical Input Requirements",
        placeholder=(
            "Describe supported image formats, "
            "resolution or image-quality requirements, "
            "and any unsupported input conditions."
        ),
        height=100,
        key="AIF-002"
    )

    profile["AIF-003"] = st.multiselect(
        "Input Sources",
        [
            "Scanner",
            "PACS",
            "EHR",
            "User upload",
            "Other"
        ],
        key="AIF-003"
    )

    if "Other" in profile["AIF-003"]:
        profile["AIF-003-OTHER"] = st.text_input(
            "Please specify the input source",
            key="AIF-003-OTHER"
        )

    profile["AIF-004"] = st.text_area(
        "AI Processing",
        placeholder=(
            "Describe how the AI processes the input "
            "information to perform its intended function."
        ),
        height=100,
        key="AIF-004"
    )

    profile["AIF-005"] = st.selectbox(
        "Image Modification",
        [
            "Select an option",
            "Yes",
            "No",
            "Unknown"
        ],
        key="AIF-005"
    )

    if profile["AIF-005"] == "Yes":
        profile["AIF-005-DETAILS"] = st.text_area(
            "Describe the image modification",
            placeholder=(
                "Explain how the image is modified "
                "and whether the original image is retained."
            ),
            height=100,
            key="AIF-005-DETAILS"
        )

    return profile
