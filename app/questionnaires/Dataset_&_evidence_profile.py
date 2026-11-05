"""D2.4 Dataset and Evidence questionnaire (Streamlit)."""
import streamlit as st

FIELD_LABELS = {
    "DEP-001": "Dataset Inventory",
    "DEP-002": "Sources, Sites and Collection Period",
    "DEP-003": "Collection Design",
    "DEP-004": "Ethics, Consent, Data-Use and Privacy Basis",
    "DEP-005": "Sample Sizes",
    "DEP-006": "Inclusion and Exclusion Criteria",
    "DEP-007": "Population Composition",
    "DEP-008": "Acquisition Characteristics",
    "DEP-009": "Preprocessing, Quality Control and Augmentation",
    "DEP-010": "Data Management and Traceability",
    "DEP-011": "Reference Standard",
    "DEP-012": "Annotation and Reading Process",
    "DEP-013": "Reference Standard Limitations",
    "DEP-014": "Partitioning and Independence",
    "DEP-015": "External or Independent Test Data",
    "DEP-016": "Representativeness of Datasets",
    "DEP-017": "Bias Assessment and Mitigation",
    "DEP-018": "Known Data Gaps and Under-Represented Groups",
    "DEP-019": "Evaluated Software and Model Versions",
    "DEP-020": "Metrics, Thresholds and Acceptance Criteria",
    "DEP-021": "Overall and Subgroup Results",
    "DEP-022": "Repeatability and Reproducibility",
    "DEP-023": "Robustness, Compatibility and Failure Testing",
    "DEP-024": "Output Uncertainty",
    "DEP-025": "Assessment of Generated or Modified Outputs",
    "DEP-026": "Software Verification and Validation Evidence",
    "DEP-027": "Valid Clinical Association",
    "DEP-028": "Clinical Performance Evidence Type",
    "DEP-029": "Clinical Study Population and Independence",
    "DEP-030": "Clinical Performance Measures and Results",
    "DEP-031": "Human-AI Team Evaluation",
    "DEP-032": "Evidence-to-Claim Alignment",
    "DEP-033": "Rationale Where No Device-Specific Clinical Data",
    "DEP-034": "Planned Human Studies and Authorization",
    "DEP-035": "Evidence Document Register",
    "DEP-036": "GMLP Implementation Description",
}

CHOICES_YNU = ["Select an option", "Yes", "No", "Unknown"]
CHOICES_YPNU = ["Select an option", "Yes", "Partly", "No", "Unknown"]
CHOICES_YNNAU = ["Select an option", "Yes", "No", "Not applicable", "Unknown"]

STUDY_TYPES = ["Retrospective analysis", "Reader study", "Prospective study",
               "Clinical investigation", "Real-world data"]


def _other_details(profile, field_id, multiple=False):
    """Show an extra text box when the user selects Other."""
    value = profile[field_id]
    selected = "Other" in value if multiple else value == "Other"
    if selected:
        profile[f"{field_id}-OTHER"] = st.text_input(
            "Please specify the other option",
            key=f"{field_id}-OTHER",
        )


def _details(profile, field_id, prompt):
    """Show a follow-up text box and store it as <field ID>-DETAILS."""
    profile[f"{field_id}-DETAILS"] = st.text_area(
        prompt, key=f"{field_id}-DETAILS", height=100,
    )


def render_dataset_evidence():
    """Render D2.4 questions and return a flat field-ID keyed response dict."""
    st.header("Dataset and Evidence")
    st.write(
        "Describe the data used to develop and test the imaging-AI software, "
        "the reference standard, and the technical and clinical evidence. "
        "This section collects product information; it does not determine "
        "regulatory classification. Answer dataset questions for every dataset "
        "listed in DEP-001. Select or enter 'Unknown' instead of guessing."
    )
    profile = {}

    # ---------------------------------------------------------------
    st.divider()
    st.subheader("01 / Dataset Provenance and Composition")
    profile["DEP-001"] = st.text_area(
        "Which datasets were used to develop, tune, test or externally evaluate the product?",
        placeholder="One entry per dataset: name and version, role (training, tuning, validation, internal test, external test), and where it is documented; enter 'Unknown' if not established.",
        key="DEP-001", height=100,
    )
    profile["DEP-002"] = st.text_area(
        "Where and when was each dataset collected?",
        placeholder="Sites or number of sites, country or region, single or multi-centre, and collection period for each dataset.",
        key="DEP-002", height=100,
    )
    profile["DEP-003"] = st.selectbox(
        "How were the datasets collected? (If they differ, choose Mixed and explain in DEP-002.)",
        ["Select an option", "Retrospective", "Prospective", "Mixed", "Unknown"],
        key="DEP-003",
    )
    profile["DEP-004"] = st.multiselect(
        "What ethics, consent and data-use basis applies to the datasets?",
        ["Ethics approval", "Consent", "Consent waiver", "Data-use agreement", "Unknown", "Other"],
        key="DEP-004",
    )
    _other_details(profile, "DEP-004", multiple=True)
    if profile["DEP-004"] and profile["DEP-004"] != ["Unknown"]:
        _details(profile, "DEP-004", "Describe the privacy requirements that apply to the data.")
    profile["DEP-005"] = st.text_area(
        "How many patients, images or scans, and sites are in each dataset, and how was the sample size justified?",
        key="DEP-005", height=100,
    )
    profile["DEP-006"] = st.text_area(
        "What inclusion and exclusion criteria were applied, and why was any data removed?",
        placeholder="Enter 'None specified' or 'Unknown' if applicable.",
        key="DEP-006", height=100,
    )
    profile["DEP-007"] = st.text_area(
        "What are the demographic and clinical characteristics of the people in each dataset?",
        placeholder="Age, sex and gender, race or ethnicity, disease stage, condition prevalence, comorbidities. Compare with the intended population in D2.1.",
        key="DEP-007", height=100,
    )
    profile["DEP-008"] = st.text_area(
        "What imaging equipment and acquisition settings produced the data?",
        placeholder="Scanner manufacturers and models, field strength, sequences or protocols, resolution, image quality; include the same for any reference modality.",
        key="DEP-008", height=100,
    )
    profile["DEP-009"] = st.multiselect(
        "Was the data preprocessed, quality-checked, augmented, or supplemented with synthetic data or imputed values?",
        ["Preprocessing", "Quality control", "Harmonization", "Co-registration", "Augmentation",
         "Synthetic data", "Imputation", "None", "Unknown", "Other"],
        key="DEP-009",
    )
    _other_details(profile, "DEP-009", multiple=True)
    if profile["DEP-009"] and not set(profile["DEP-009"]) <= {"None", "Unknown"}:
        _details(profile, "DEP-009", "Describe each step used and why.")
    profile["DEP-010"] = st.text_area(
        "How are datasets versioned, access-controlled and traced to the model versions built or tested with them?",
        key="DEP-010", height=100,
    )

    # ---------------------------------------------------------------
    st.divider()
    st.subheader("02 / Reference Standard and Annotation")
    profile["DEP-011"] = st.multiselect(
        "What reference standard (ground truth) was used to train or evaluate the product?",
        ["Acquired reference image", "Expert read", "Pathology", "Clinical outcome", "Composite", "Unknown", "Other"],
        key="DEP-011",
    )
    _other_details(profile, "DEP-011", multiple=True)
    if profile["DEP-011"] and profile["DEP-011"] != ["Unknown"]:
        _details(profile, "DEP-011",
                 "Describe the reference standard and why it is appropriate. For an acquired image, include the modality, protocol, and any tracer, reconstruction and timing relationship to the input.")
    if "Expert read" in profile["DEP-011"]:
        profile["DEP-012"] = st.text_area(
            "How were the expert readers selected, and how were disagreements handled?",
            placeholder="Number of readers, qualifications, blinding, adjudication, inter-reader variability.",
            key="DEP-012", height=100,
        )
    profile["DEP-013"] = st.text_area(
        "What are the known limitations or uncertainties of the reference standard?",
        placeholder="Enter 'None identified' with a justification, or 'Unknown'.",
        key="DEP-013", height=100,
    )

    # ---------------------------------------------------------------
    st.divider()
    st.subheader("03 / Partitioning, Representativeness and Bias")
    profile["DEP-014"] = st.selectbox(
        "How was the data split into training, tuning and test sets (unit of split)?",
        ["Select an option", "Patient", "Site", "Scan", "Other", "Unknown"],
        key="DEP-014",
    )
    if profile["DEP-014"] in ("Patient", "Site", "Scan", "Other"):
        _details(profile, "DEP-014",
                 "Describe how independence between sets was ensured, how repeat or longitudinal scans were handled, and when the test set was locked.")
    profile["DEP-015"] = st.selectbox(
        "Was the product tested on external or independent data from sites, scanners or periods not used in development?",
        CHOICES_YNU, key="DEP-015",
    )
    if profile["DEP-015"] == "Yes":
        _details(profile, "DEP-015", "Describe the external data (sites, scanners, time period).")
    profile["DEP-016"] = st.selectbox(
        "Do the datasets represent the intended patient population, imaging equipment and care settings?",
        CHOICES_YPNU, key="DEP-016",
    )
    if profile["DEP-016"] in ("Yes", "Partly", "No"):
        _details(profile, "DEP-016",
                 "Explain, with reference to the intended population and setting in D2.1 and the markets targeted.")
    profile["DEP-017"] = st.text_area(
        "How were bias and performance differences across subgroups identified, and what was done to reduce them?",
        placeholder="Enter 'None performed' or 'Unknown' if applicable.",
        key="DEP-017", height=100,
    )
    profile["DEP-018"] = st.text_area(
        "What data gaps, under-represented groups or other data limitations are known?",
        placeholder="Enter 'None identified' with a justification, or 'Unknown'.",
        key="DEP-018", height=100,
    )

    # ---------------------------------------------------------------
    st.divider()
    st.subheader("04 / Technical Performance Evidence")
    profile["DEP-019"] = st.selectbox(
        "Is the evaluated software and model version the version intended for release?",
        CHOICES_YNU, key="DEP-019",
    )
    if profile["DEP-019"] in ("Yes", "No"):
        _details(profile, "DEP-019",
                 "Identify the versions evaluated and describe any differences from the release version.")
    profile["DEP-020"] = st.multiselect(
        "Which performance metrics were used?",
        ["Accuracy", "Sensitivity", "Specificity", "Precision", "Image-similarity",
         "Quantitative agreement", "Unknown", "Other"],
        key="DEP-020",
    )
    _other_details(profile, "DEP-020", multiple=True)
    if profile["DEP-020"] and profile["DEP-020"] != ["Unknown"]:
        _details(profile, "DEP-020",
                 "Give the operating thresholds and acceptance criteria, whether they were set before testing, and the justification.")
    profile["DEP-021"] = st.multiselect(
        "Were results reported by subgroup, site or scanner?",
        ["Sex or gender", "Age", "Disease stage", "Site", "Scanner", "Other", "None", "Unknown"],
        key="DEP-021",
    )
    _other_details(profile, "DEP-021", multiple=True)
    if profile["DEP-021"] and not set(profile["DEP-021"]) <= {"None", "Unknown"}:
        _details(profile, "DEP-021", "State whether these analyses were pre-specified and where the results are reported.")
    profile["DEP-022"] = st.selectbox(
        "Was repeatability and reproducibility of the output tested?",
        CHOICES_YNNAU, key="DEP-022",
    )
    if profile["DEP-022"] == "Yes":
        _details(profile, "DEP-022", "Describe the testing.")
    elif profile["DEP-022"] == "Not applicable":
        _details(profile, "DEP-022", "Explain why this is not applicable (for example, the output is not a measurement).")
    profile["DEP-023"] = st.selectbox(
        "Was the product tested with supported devices, poor-quality or unexpected inputs, and failure conditions?",
        CHOICES_YPNU, key="DEP-023",
    )
    if profile["DEP-023"] in ("Yes", "Partly"):
        _details(profile, "DEP-023", "Describe the devices tested and the unexpected, poor-quality or out-of-scope inputs tried.")
    profile["DEP-024"] = st.selectbox(
        "Does the product estimate uncertainty in its output?",
        CHOICES_YNU, key="DEP-024",
    )
    if profile["DEP-024"] == "Yes":
        _details(profile, "DEP-024", "Describe the estimate and the evidence that it is reliable.")
    profile["DEP-025"] = st.selectbox(
        "If the product alters or creates images, was the fidelity and plausibility of its output assessed?",
        CHOICES_YNNAU, key="DEP-025",
    )
    if profile["DEP-025"] == "Yes":
        _details(profile, "DEP-025",
                 "Describe the methods used and how missing, invented or misleading features were assessed. Similarity to a reference alone may not support a clinical claim.")
    elif profile["DEP-025"] == "Not applicable":
        _details(profile, "DEP-025", "Explain why this is not applicable (for example, the product does not alter or create images).")
    profile["DEP-026"] = st.selectbox(
        "Are software verification and validation records available for the whole software function?",
        CHOICES_YPNU, key="DEP-026",
    )
    if profile["DEP-026"] in ("Yes", "Partly"):
        _details(profile, "DEP-026", "State the lifecycle standard used (for example IEC 62304) and any documentation level, and where the records are.")

    # ---------------------------------------------------------------
    st.divider()
    st.subheader("05 / Clinical Evidence")
    profile["DEP-027"] = st.multiselect(
        "What evidence shows the output is clinically associated with the condition the product addresses?",
        ["Literature", "Clinical guidelines", "Proof-of-concept study", "Existing clinical data",
         "Manufacturer study", "None", "Unknown"],
        key="DEP-027",
    )
    if profile["DEP-027"] and not set(profile["DEP-027"]) <= {"None", "Unknown"}:
        _details(profile, "DEP-027", "Cite the evidence and explain how it supports the link.")
    profile["DEP-028"] = st.multiselect(
        "What type of clinical performance evidence exists?",
        STUDY_TYPES + ["Literature only", "None yet", "Unknown"],
        key="DEP-028",
    )
    if any(x in STUDY_TYPES for x in profile["DEP-028"]):
        profile["DEP-029"] = st.text_area(
            "Who was in the clinical study, and was the study population independent of the data used to develop the product?",
            placeholder="Population, relevant subgroups, independence from development data, relevance to intended practice.",
            key="DEP-029", height=100,
        )
        profile["DEP-030"] = st.text_area(
            "What clinical performance measures and results were reported, and compared with what?",
            placeholder="Sensitivity, specificity, predictive values, likelihood ratios, confidence intervals, comparator (standard of care or acquired reference), limitations.",
            key="DEP-030", height=100,
        )
    profile["DEP-031"] = st.selectbox(
        "Was the combined performance of users and the AI evaluated?",
        CHOICES_YNNAU, key="DEP-031",
    )
    if profile["DEP-031"] == "Yes":
        _details(profile, "DEP-031", "Describe the evaluation (for example a reader study or usability testing).")
    elif profile["DEP-031"] == "Not applicable":
        _details(profile, "DEP-031", "Explain why this is not applicable (for example, no user interacts with or acts on the output).")
    profile["DEP-032"] = st.selectbox(
        "Does the clinical evidence directly support each clinical application and use claimed in D2.1 and D2.2?",
        CHOICES_YPNU, key="DEP-032",
    )
    if profile["DEP-032"] in ("Yes", "Partly", "No"):
        _details(profile, "DEP-032", "Explain for each claim how the evidence supports it, or where it does not.")
    if "Literature only" in profile["DEP-028"] or "None yet" in profile["DEP-028"]:
        profile["DEP-033"] = st.text_area(
            "With no device-specific clinical data, what rationale shows the available evidence is sufficient?",
            key="DEP-033", height=100,
        )
    profile["DEP-034"] = st.selectbox(
        "Is a study on human participants planned or under way?",
        CHOICES_YNU, key="DEP-034",
    )
    if profile["DEP-034"] == "Yes":
        _details(profile, "DEP-034", "Where will it take place, and what ethics or regulatory authorization has been identified or obtained?")

    # ---------------------------------------------------------------
    st.divider()
    st.subheader("06 / Evidence Documentation")
    profile["DEP-035"] = st.text_area(
        "Which documents support your answers?",
        placeholder="One entry per document: title, document ID, version, date, page or section, and the DEP fields it supports.",
        key="DEP-035", height=120,
    )
    profile["DEP-036"] = st.selectbox(
        "Has the developer documented how Good Machine Learning Practice (GMLP) principles were considered?",
        ["Select an option", "Yes", "Partly", "No", "Not applicable", "Unknown"],
        key="DEP-036",
    )
    if profile["DEP-036"] in ("Yes", "Partly"):
        _details(profile, "DEP-036", "Reference the document that describes it.")
    elif profile["DEP-036"] == "Not applicable":
        _details(profile, "DEP-036", "Explain why this is not applicable (for example, no Health Canada or FDA machine learning submission is planned).")

    return profile
