# to run code inter in terminal: python -m streamlit run app/sample_interface.py
import streamlit as st

st.set_page_config(
    page_title="AI Regulatory Readiness Platform",
    layout="wide"
)

# Professional styling
st.markdown("""
<style>
    .stApp {
        background-color: #F6F8FB;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
    }

    h1 {
        color: #183153;
        font-weight: 650;
    }

    h3 {
        color: #263F5B;
    }

    div.stButton > button[kind="primary"] {
        background-color: #245A81;
        color: white;
        border-radius: 6px;
        border: none;
    }

    .demo-label {
        background-color: #EAF0F7;
        color: #36536D;
        padding: 10px 15px;
        border-radius: 6px;
        font-size: 13px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.caption("IMAGING AI | REGULATORY GUIDANCE")

st.title("AI Regulatory Readiness Platform")

st.markdown("""
<div class="demo-label">
    <strong>Concept Prototype</strong> —
    Illustrative interface
    Regulatory decision-making and readiness assessment functions are not yet implemented.
</div>
""", unsafe_allow_html=True)

st.subheader("AI Model Profile")

st.write(
    "Provide information about your imaging AI technology "
    "to begin a preliminary regulatory assessment."
)

st.divider()

# Section 1
st.markdown("### 01 / Product Information")

model_name = st.text_input(
    "AI Model Name",
    value="Lung Nodule Detection AI"
)

col1, col2 = st.columns(2)

with col1:
    jurisdiction = st.selectbox(
        "Target Jurisdiction",
        ["Canada", "United States", "European Union"]
    )

with col2:
    modality = st.selectbox(
        "Imaging Modality",
        ["CT", "MRI", "X-ray", "Ultrasound", "Other"]
    )

intended_use = st.text_area(
    "Intended Purpose",
    value="Detect suspicious lung nodules in CT images "
          "to assist radiologist interpretation.",
    height=90
)

st.divider()

# Section 2
st.markdown("### 02 / Clinical Function")

col3, col4 = st.columns(2)

with col3:
    intended_user = st.selectbox(
        "Intended User",
        ["Radiologist", "Physician", "Healthcare Professional", "Other"]
    )

with col4:
    clinical_role = st.selectbox(
        "Clinical Role",
        [
            "Assists clinical interpretation",
            "Provides diagnostic recommendations",
            "Supports treatment planning",
            "Other"
        ]
    )

oversight = st.selectbox(
    "Human Oversight",
    [
        "Clinician reviews AI output",
        "Limited clinician oversight",
        "Other"
    ]
)

st.divider()

# Section 3
st.markdown("### 03 / AI Characteristics")

model_type = st.selectbox(
    "Model Behaviour",
    ["Locked Model", "Adaptive Model"]
)

st.info(
    "Target scope: Imaging AI technologies approximately within TRL 4–7."
)

st.markdown("")

if st.button("Preview Model Profile", type="primary"):

    st.divider()
    st.subheader("Model Profile Summary")

    st.write("**Model:**", model_name)
    st.write("**Jurisdiction:**", jurisdiction)
    st.write("**Imaging Modality:**", modality)
    st.write("**Intended Purpose:**", intended_use)
    st.write("**Intended User:**", intended_user)
    st.write("**Clinical Role:**", clinical_role)
    st.write("**Human Oversight:**", oversight)
    st.write("**Model Behaviour:**", model_type)

    st.caption(
        "Demonstration only. No regulatory classification "
        "or readiness determination has been performed."
    )
