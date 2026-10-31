import streamlit as st

def render_product_profile():

    st.header("Product and Intended-Use Profile")

    st.write(
        "Provide information about your imaging AI product."
    )

    st.subheader("01 / Product Identification")

    product_name = st.text_input(
        "PIP-001: Product Name and Version",
        placeholder="Example: Lung Nodule Detection AI, Version 1.0"
    )

    return {
        "PIP-001": product_name
    }
