import streamlit as st
from product_profile import render_product_profile

st.set_page_config(
    page_title="AI Regulatory Readiness Platform",
    layout="wide"
)

st.title("AI Regulatory Readiness Platform")

# Display Deliverable 2.1 questionnaire
profile = render_product_profile()

# Display the information entered
if st.button("Preview Product Profile"):
    st.subheader("Product Profile Summary")
    st.write(profile)
