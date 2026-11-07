"""D2.4 Dataset and Evidence Profile questionnaire."""

import streamlit as st


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def show_details(prompt, key, height=100, placeholder=""):
    """Display a text area and return its response."""
    return st.text_area(
        prompt,
        key=key,
        height=height,
        placeholder=placeholder,
    )


def show_other(selected, key, label="Describe the other option"):
    """Ask for a description when Other is selected."""
    if "Other" in selected:
        return st.text_input(label, key=key)
    return None


def yes_no_unknown(prompt, key):
    """Yes / No / Unknown response."""
    return st.selectbox(
        prompt,
        ["Select an option", "Yes", "No", "Unknown"],
        key=key,
    )


def yes_partly_no_unknown(prompt, key):
    """Yes / Partly / No / Unknown response."""
    return st.selectbox(
        prompt,
        ["Select an option", "Yes", "Partly", "No", "Unknown"],
        key=key,
    )


# ============================================================
# MAIN QUESTIONNAIRE
# ============================================================

def render_dataset_evidence():

    st.header("Dataset and Evidence Profile")

    st.write(
        "Describe the data used to develop, tune and test the "
        "imaging-AI product, its reference standard, and its "
        "technical and clinical evidence."
    )

    st.info(
        "Complete all required fields. If an answer is unknown, "
        "select or enter 'Unknown' and explain the gap; do not guess. "
        "Select 'Other' or 'Not applicable' only with a description "
        "or justification. Dataset questions are answered once per "
        "dataset. Technical and clinical evidence questions are "
        "answered once per AI function and evaluated version. "
        "Use DEP-035 to identify documents supporting your answers."
    )

    profile = {}

    # ========================================================
    # 01 / DATASET PROVENANCE AND COMPOSITION
    # DEP-001 TO DEP-010
    # ========================================================

    st.divider()
    st.subheader("01 / Dataset Provenance and Composition")

    st.write(
        "Enter each dataset separately. DEP-001 to DEP-018 will "
        "be collected for every dataset."
    )

    dataset_count = st.number_input(
        "How many datasets are being reported?",
        min_value=1,
        max_value=50,
        value=1,
        step=1,
        key="dataset-count",
    )

    profile["datasets"] = []

    for i in range(int(dataset_count)):

        dataset = {}

        with st.expander(
            f"Dataset {i + 1}",
            expanded=(i == 0),
        ):

            # ------------------------------------------------
            # DEP-001 — Dataset Inventory
            # ------------------------------------------------

            st.markdown("**DEP-001 — Dataset Inventory**")

            st.write(
                "List each dataset used to develop, tune, test or "
                "externally evaluate the product."
            )

            dataset["DEP-001"] = {}

            dataset["DEP-001"]["dataset_name_version"] = st.text_input(
                "Dataset name and version",
                key=f"dataset-{i}-DEP-001-name",
            )

            dataset["DEP-001"]["role"] = st.multiselect(
                "What role did this dataset serve?",
                [
                    "Training",
                    "Tuning",
                    "Validation",
                    "Internal test",
                    "External test",
                    "Other",
                ],
                key=f"dataset-{i}-DEP-001-role",
            )

            dataset["DEP-001"]["role_other"] = show_other(
                dataset["DEP-001"]["role"],
                f"dataset-{i}-DEP-001-role-other",
            )

            dataset["DEP-001"]["source_documentation"] = st.text_input(
                "Link to source documentation",
                key=f"dataset-{i}-DEP-001-source",
            )

            # ------------------------------------------------
            # DEP-002 — Sources, Sites and Collection Period
            # ------------------------------------------------

            st.markdown(
                "**DEP-002 — Sources, Sites and Collection Period**"
            )

            dataset["DEP-002"] = show_details(
                "Where and when was this dataset collected, "
                "and from how many sites and countries?",
                f"dataset-{i}-DEP-002",
                height=120,
                placeholder=(
                    "Sites (names or de-identified count); country "
                    "or region; single or multi-centre; collection "
                    "period; Unknown."
                ),
            )

            # ------------------------------------------------
            # DEP-003 — Collection Design
            # ------------------------------------------------

            st.markdown("**DEP-003 — Collection Design**")

            dataset["DEP-003"] = st.selectbox(
                "Was this dataset collected retrospectively, "
                "prospectively or both?",
                [
                    "Select an option",
                    "Retrospective",
                    "Prospective",
                    "Mixed",
                    "Unknown",
                ],
                key=f"dataset-{i}-DEP-003",
            )

            # ------------------------------------------------
            # DEP-004 — Ethics, Consent, Data-Use and Privacy
            # ------------------------------------------------

            st.markdown(
                "**DEP-004 — Ethics, Consent, Data-Use and Privacy Basis**"
            )

            dataset["DEP-004"] = st.multiselect(
                "What ethics approval, consent or waiver, data-use "
                "agreement and privacy basis applies to this dataset?",
                [
                    "Ethics approval",
                    "Consent or waiver",
                    "Data-use agreement",
                    "Other",
                    "Unknown",
                ],
                key=f"dataset-{i}-DEP-004",
            )

            dataset["DEP-004-other"] = show_other(
                dataset["DEP-004"],
                f"dataset-{i}-DEP-004-other",
            )

            if dataset["DEP-004"]:
                dataset["DEP-004-details"] = show_details(
                    "Describe the applicable privacy requirements "
                    "and relevant ethics, consent, waiver or "
                    "data-use details.",
                    f"dataset-{i}-DEP-004-details",
                )
            else:
                dataset["DEP-004-details"] = None

            # ------------------------------------------------
            # DEP-005 — Sample Sizes
            # ------------------------------------------------

            st.markdown("**DEP-005 — Sample Sizes**")

            dataset["DEP-005"] = show_details(
                "How many patients, images or scans, and sites are "
                "in this dataset, and how was the sample size justified?",
                f"dataset-{i}-DEP-005",
                height=120,
                placeholder=(
                    "Number of patients; number of scans or images; "
                    "number of sites; sample-size rationale; Unknown."
                ),
            )

            # ------------------------------------------------
            # DEP-006 — Inclusion and Exclusion Criteria
            # ------------------------------------------------

            st.markdown(
                "**DEP-006 — Inclusion and Exclusion Criteria**"
            )

            dataset["DEP-006"] = show_details(
                "What inclusion and exclusion criteria were applied, "
                "and why was any data removed?",
                f"dataset-{i}-DEP-006",
                height=120,
                placeholder="Enter 'None specified' or 'Unknown' where appropriate.",
            )

            # ------------------------------------------------
            # DEP-007 — Population Composition
            # ------------------------------------------------

            st.markdown("**DEP-007 — Population Composition**")

            dataset["DEP-007"] = show_details(
                "What are the demographic and clinical "
                "characteristics of the people in this dataset?",
                f"dataset-{i}-DEP-007",
                height=140,
                placeholder=(
                    "Age; sex and gender; race or ethnicity; disease "
                    "stage; condition prevalence; comorbidities; "
                    "other relevant characteristics. Enter Unknown "
                    "for any item that is not known."
                ),
            )

            # ------------------------------------------------
            # DEP-008 — Acquisition Characteristics
            # ------------------------------------------------

            st.markdown(
                "**DEP-008 — Acquisition Characteristics**"
            )

            dataset["DEP-008"] = show_details(
                "What imaging equipment and acquisition settings "
                "produced the data?",
                f"dataset-{i}-DEP-008",
                height=140,
                placeholder=(
                    "Scanner manufacturers and models; field strength; "
                    "sequences or protocols; resolution; image-quality "
                    "characteristics. For any reference modality, also "
                    "include its acquisition parameters; Unknown."
                ),
            )

            # ------------------------------------------------
            # DEP-009 — Preprocessing and Quality Control
            # ------------------------------------------------

            st.markdown(
                "**DEP-009 — Preprocessing, Quality Control "
                "and Augmentation**"
            )

            dataset["DEP-009"] = st.multiselect(
                "Was the data preprocessed, quality-checked, "
                "augmented or supplemented with synthetic data "
                "or imputed values?",
                [
                    "Preprocessing",
                    "Quality control",
                    "Harmonization",
                    "Co-registration",
                    "Augmentation",
                    "Synthetic data",
                    "Imputation",
                    "None",
                    "Unknown",
                ],
                key=f"dataset-{i}-DEP-009",
            )

            if (
                dataset["DEP-009"]
                and not set(dataset["DEP-009"]).issubset(
                    {"None", "Unknown"}
                )
            ):
                dataset["DEP-009-details"] = show_details(
                    "Describe each method used.",
                    f"dataset-{i}-DEP-009-details",
                )
            else:
                dataset["DEP-009-details"] = None

            # ------------------------------------------------
            # DEP-010 — Data Management and Traceability
            # ------------------------------------------------

            st.markdown(
                "**DEP-010 — Data Management and Traceability**"
            )

            dataset["DEP-010"] = show_details(
                "How are datasets versioned, access-controlled "
                "and traced to the model versions built or tested "
                "with them?",
                f"dataset-{i}-DEP-010",
                height=120,
                placeholder=(
                    "Describe version control, access controls "
                    "and traceability; Unknown."
                ),
            )

            # =================================================
            # 02 / REFERENCE STANDARD AND ANNOTATION
            # DEP-011 TO DEP-013
            # =================================================

            st.divider()
            st.markdown("### 02 / Reference Standard and Annotation")

            # DEP-011

            st.markdown("**DEP-011 — Reference Standard**")

            dataset["DEP-011"] = st.multiselect(
                "What reference standard (ground truth) was used "
                "to train or evaluate the product, and why is "
                "it appropriate?",
                [
                    "Acquired reference image",
                    "Expert read",
                    "Pathology",
                    "Clinical outcome",
                    "Composite",
                    "Other",
                    "Unknown",
                ],
                key=f"dataset-{i}-DEP-011",
            )

            dataset["DEP-011-other"] = show_other(
                dataset["DEP-011"],
                f"dataset-{i}-DEP-011-other",
            )

            if dataset["DEP-011"]:
                dataset["DEP-011-details"] = show_details(
                    "Describe the reference standard and the "
                    "rationale for why it is appropriate. If an "
                    "acquired reference image was used, include "
                    "its modality, protocol, tracer, reconstruction "
                    "and timing relationship to the input.",
                    f"dataset-{i}-DEP-011-details",
                    height=140,
                )
            else:
                dataset["DEP-011-details"] = None

            # DEP-012

            st.markdown(
                "**DEP-012 — Expert Selection and Agreement**"
            )

            annotation_used = st.selectbox(
                "Were expert reads or expert annotations used "
                "to produce or check the reference?",
                [
                    "Select an option",
                    "Yes",
                    "No",
                    "Unknown",
                ],
                key=f"dataset-{i}-DEP-012-trigger",
            )

            if (
                "Expert read" in dataset["DEP-011"]
                or annotation_used == "Yes"
            ):
                dataset["DEP-012"] = show_details(
                    "If experts produced or checked the reference, "
                    "how were they selected and how were disagreements "
                    "handled?",
                    f"dataset-{i}-DEP-012",
                    height=120,
                    placeholder=(
                        "Number of readers; qualifications; blinding; "
                        "adjudication method; inter-reader variability; "
                        "Unknown."
                    ),
                )
            else:
                dataset["DEP-012"] = None

            # DEP-013

            st.markdown(
                "**DEP-013 — Reference Standard Limitations**"
            )

            dataset["DEP-013"] = show_details(
                "What are the known limitations or uncertainties "
                "of the reference standard?",
                f"dataset-{i}-DEP-013",
                height=120,
                placeholder=(
                    "Enter 'None identified' with a justification, "
                    "or 'Unknown'."
                ),
            )

            # =================================================
            # 03 / PARTITIONING, REPRESENTATIVENESS AND BIAS
            # DEP-014 TO DEP-018
            # =================================================

            st.divider()
            st.markdown(
                "### 03 / Partitioning, Representativeness and Bias"
            )

            # DEP-014

            st.markdown(
                "**DEP-014 — Partitioning and Independence**"
            )

            dataset["DEP-014"] = st.selectbox(
                "How was the data split into training, tuning "
                "and test sets?",
                [
                    "Select an option",
                    "Patient",
                    "Site",
                    "Scan",
                    "Other",
                    "Unknown",
                ],
                key=f"dataset-{i}-DEP-014",
            )

            if dataset["DEP-014"] == "Other":
                dataset["DEP-014-other"] = st.text_input(
                    "Describe the other unit of split",
                    key=f"dataset-{i}-DEP-014-other",
                )
            else:
                dataset["DEP-014-other"] = None

            dataset["DEP-014-details"] = show_details(
                "Describe how independence between sets was ensured, "
                "including handling of repeat or longitudinal scans, "
                "leakage controls, and when the test set was locked.",
                f"dataset-{i}-DEP-014-details",
                height=120,
            )

            # DEP-015

            st.markdown(
                "**DEP-015 — External or Independent Test Data**"
            )

            dataset["DEP-015"] = yes_no_unknown(
                "Was the product tested on external or independent "
                "data from sites, scanners or periods not used "
                "in development?",
                f"dataset-{i}-DEP-015",
            )

            if dataset["DEP-015"] == "Yes":
                dataset["DEP-015-details"] = show_details(
                    "Describe the external data.",
                    f"dataset-{i}-DEP-015-details",
                )
            else:
                dataset["DEP-015-details"] = None

            # DEP-016

            st.markdown(
                "**DEP-016 — Representativeness of Datasets**"
            )

            dataset["DEP-016"] = yes_partly_no_unknown(
                "How well do the datasets represent the intended "
                "patient population, imaging equipment and care settings?",
                f"dataset-{i}-DEP-016",
            )

            if dataset["DEP-016"] in ("Yes", "Partly", "No"):
                dataset["DEP-016-details"] = show_details(
                    "Explain by reference to PIP-006, PIP-011 to "
                    "PIP-014 and PIP-016, including relevance "
                    "to the markets targeted.",
                    f"dataset-{i}-DEP-016-details",
                )
            else:
                dataset["DEP-016-details"] = None

            # DEP-017

            st.markdown(
                "**DEP-017 — Bias Assessment and Mitigation**"
            )

            dataset["DEP-017"] = show_details(
                "How were bias and performance differences across "
                "subgroups identified, and what was done to reduce them?",
                f"dataset-{i}-DEP-017",
                height=120,
                placeholder=(
                    "Describe methods used to identify bias and any "
                    "mitigation; enter 'None performed' or 'Unknown' "
                    "where appropriate."
                ),
            )

            # DEP-018

            st.markdown(
                "**DEP-018 — Known Data Gaps and Under-Represented Groups**"
            )

            dataset["DEP-018"] = show_details(
                "What data gaps, under-represented groups or other "
                "data limitations are known?",
                f"dataset-{i}-DEP-018",
                height=120,
                placeholder=(
                    "Enter 'None identified' with a justification, "
                    "or 'Unknown'."
                ),
            )

        profile["datasets"].append(dataset)

    # ========================================================
    # 04 / TECHNICAL PERFORMANCE EVIDENCE
    # DEP-019 TO DEP-026
    # ========================================================

    st.divider()
    st.subheader("04 / Technical Performance Evidence")

    st.write(
        "Complete this section separately for each AI function "
        "and evaluated software/model version."
    )

    function_count = st.number_input(
        "How many AI function and evaluated-version records "
        "are being reported?",
        min_value=1,
        max_value=50,
        value=1,
        step=1,
        key="function-count",
    )

    profile["ai_function_versions"] = []

    for i in range(int(function_count)):

        function = {}

        with st.expander(
            f"AI Function / Evaluated Version {i + 1}",
            expanded=(i == 0),
        ):

            # ------------------------------------------------
            # DEP-019 — Evaluated Versions
            # ------------------------------------------------

            st.markdown(
                "**DEP-019 — Evaluated Software and Model Versions**"
            )

            function["DEP-019-versions"] = st.text_input(
                "Which software and model versions were evaluated?",
                key=f"function-{i}-DEP-019-versions",
            )

            function["DEP-019-release"] = yes_no_unknown(
                "Are they the version intended for release?",
                f"function-{i}-DEP-019-release",
            )

            if function["DEP-019-release"] == "No":
                function["DEP-019-differences"] = show_details(
                    "Describe the differences from the release version.",
                    f"function-{i}-DEP-019-differences",
                )
            else:
                function["DEP-019-differences"] = None

            # ------------------------------------------------
            # DEP-020 — Metrics and Acceptance Criteria
            # ------------------------------------------------

            st.markdown(
                "**DEP-020 — Metrics, Thresholds and Acceptance Criteria**"
            )

            function["DEP-020-metrics"] = st.multiselect(
                "Which performance metrics were used?",
                [
                    "Accuracy",
                    "Sensitivity",
                    "Specificity",
                    "Precision",
                    "Image-similarity",
                    "Quantitative agreement",
                    "Other",
                ],
                key=f"function-{i}-DEP-020-metrics",
            )

            function["DEP-020-other"] = show_other(
                function["DEP-020-metrics"],
                f"function-{i}-DEP-020-other",
            )

            function["DEP-020-thresholds"] = show_details(
                "Describe the operating thresholds.",
                f"function-{i}-DEP-020-thresholds",
                height=80,
            )

            function["DEP-020-criteria"] = show_details(
                "Describe the acceptance criteria.",
                f"function-{i}-DEP-020-criteria",
                height=80,
            )

            function["DEP-020-prespecified"] = yes_no_unknown(
                "Were the thresholds and acceptance criteria "
                "set before testing?",
                f"function-{i}-DEP-020-prespecified",
            )

            function["DEP-020-justification"] = show_details(
                "Provide the justification for the selected metrics, "
                "thresholds and acceptance criteria.",
                f"function-{i}-DEP-020-justification",
            )

            # ------------------------------------------------
            # DEP-021 — Overall and Subgroup Results
            # ------------------------------------------------

            st.markdown(
                "**DEP-021 — Overall and Subgroup Results**"
            )

            function["DEP-021-overall"] = yes_no_unknown(
                "Were overall results reported?",
                f"function-{i}-DEP-021-overall",
            )

            function["DEP-021-subgroups"] = st.multiselect(
                "Which subgroups were analysed?",
                [
                    "Sex or gender",
                    "Age",
                    "Disease stage",
                    "Site",
                    "Scanner",
                    "Other",
                    "None",
                ],
                key=f"function-{i}-DEP-021-subgroups",
            )

            function["DEP-021-other"] = show_other(
                function["DEP-021-subgroups"],
                f"function-{i}-DEP-021-other",
            )

            function["DEP-021-prespecified"] = yes_no_unknown(
                "Were the subgroup analyses pre-specified?",
                f"function-{i}-DEP-021-prespecified",
            )

            function["DEP-021-report"] = st.text_input(
                "Link to the report containing the results",
                key=f"function-{i}-DEP-021-report",
            )

            # ------------------------------------------------
            # DEP-022 — Repeatability and Reproducibility
            # ------------------------------------------------

            st.markdown(
                "**DEP-022 — Repeatability and Reproducibility**"
            )

            function["DEP-022-trigger"] = st.selectbox(
                "Is the output quantitative or an image-derived measurement?",
                [
                    "Select an option",
                    "Yes",
                    "No",
                    "Unknown",
                ],
                key=f"function-{i}-DEP-022-trigger",
            )

            if function["DEP-022-trigger"] == "Yes":
                function["DEP-022"] = st.selectbox(
                    "Was repeatability and reproducibility of the "
                    "output tested?",
                    [
                        "Select an option",
                        "Yes",
                        "No",
                        "Not applicable",
                        "Unknown",
                    ],
                    key=f"function-{i}-DEP-022",
                )

                if function["DEP-022"] in ("Yes", "Not applicable"):
                    function["DEP-022-details"] = show_details(
                        "Describe the testing or justify why "
                        "it is not applicable.",
                        f"function-{i}-DEP-022-details",
                    )
                else:
                    function["DEP-022-details"] = None
            else:
                function["DEP-022"] = None
                function["DEP-022-details"] = None

            # ------------------------------------------------
            # DEP-023 — Robustness and Failure Testing
            # ------------------------------------------------

            st.markdown(
                "**DEP-023 — Robustness, Compatibility and Failure Testing**"
            )

            function["DEP-023"] = yes_partly_no_unknown(
                "Was the product tested with supported devices, "
                "poor-quality or unexpected inputs, and failure conditions?",
                f"function-{i}-DEP-023",
            )

            if function["DEP-023"] in ("Yes", "Partly"):
                function["DEP-023-details"] = show_details(
                    "Describe supported devices tested and the "
                    "unexpected, poor-quality or out-of-scope "
                    "inputs tried.",
                    f"function-{i}-DEP-023-details",
                )
            else:
                function["DEP-023-details"] = None

            # ------------------------------------------------
            # DEP-024 — Output Uncertainty
            # ------------------------------------------------

            st.markdown("**DEP-024 — Output Uncertainty**")

            function["DEP-024"] = yes_no_unknown(
                "Does the product estimate uncertainty in its output?",
                f"function-{i}-DEP-024",
            )

            if function["DEP-024"] == "Yes":
                function["DEP-024-details"] = show_details(
                    "Describe the uncertainty estimate and the "
                    "evidence supporting it.",
                    f"function-{i}-DEP-024-details",
                )
            else:
                function["DEP-024-details"] = None

            # ------------------------------------------------
            # DEP-025 — Generated or Modified Images
            # ------------------------------------------------

            st.markdown(
                "**DEP-025 — Assessment of Generated or Modified Outputs**"
            )

            function["DEP-025-trigger"] = st.selectbox(
                "Does AIF-005 indicate that the product modifies "
                "images, or does AIF-006 include a transformed image?",
                [
                    "Select an option",
                    "Yes",
                    "No",
                    "Unknown",
                ],
                key=f"function-{i}-DEP-025-trigger",
            )

            if function["DEP-025-trigger"] == "Yes":

                function["DEP-025"] = st.multiselect(
                    "How were fidelity, plausibility and any missing "
                    "or invented features assessed?",
                    [
                        "Comparison with reference",
                        "Reader assessment",
                        "Quantitative agreement",
                        "Other",
                        "None",
                        "Unknown",
                    ],
                    key=f"function-{i}-DEP-025",
                )

                function["DEP-025-other"] = show_other(
                    function["DEP-025"],
                    f"function-{i}-DEP-025-other",
                )

                if (
                    function["DEP-025"]
                    and not set(function["DEP-025"]).issubset(
                        {"None", "Unknown"}
                    )
                ):
                    function["DEP-025-details"] = show_details(
                        "Describe the findings and limitations "
                        "of the assessment.",
                        f"function-{i}-DEP-025-details",
                    )
                else:
                    function["DEP-025-details"] = None

            else:
                function["DEP-025"] = None
                function["DEP-025-other"] = None
                function["DEP-025-details"] = None

            # ------------------------------------------------
            # DEP-026 — Software Verification and Validation
            # ------------------------------------------------

            st.markdown(
                "**DEP-026 — Software Verification and Validation Evidence**"
            )

            function["DEP-026-records"] = st.selectbox(
                "Are software verification and validation records "
                "available for the whole software function?",
                [
                    "Select an option",
                    "Yes",
                    "Partly",
                    "No",
                    "Unknown",
                ],
                key=f"function-{i}-DEP-026-records",
            )

            function["DEP-026-standard"] = st.selectbox(
                "Which lifecycle standard or documentation level was used?",
                [
                    "Select an option",
                    "IEC 62304",
                    "Other",
                    "None",
                    "Unknown",
                ],
                key=f"function-{i}-DEP-026-standard",
            )

            function["DEP-026-standard-other"] = show_other(
                [function["DEP-026-standard"]],
                f"function-{i}-DEP-026-standard-other",
            )

            function["DEP-026-fda-level"] = st.selectbox(
                "What FDA documentation level applies?",
                [
                    "Select an option",
                    "Basic",
                    "Enhanced",
                    "Unknown",
                    "Not pursuing FDA",
                ],
                key=f"function-{i}-DEP-026-fda-level",
            )

            # =================================================
            # 05 / CLINICAL EVIDENCE
            # DEP-027 TO DEP-034
            # =================================================

            st.divider()
            st.markdown("### 05 / Clinical Evidence")

            # DEP-027

            st.markdown("**DEP-027 — Valid Clinical Association**")

            function["DEP-027"] = st.multiselect(
                "What evidence shows that the output is clinically "
                "associated with the condition the product addresses?",
                [
                    "Literature",
                    "Clinical guidelines",
                    "Proof-of-concept study",
                    "Existing clinical data",
                    "Manufacturer study",
                    "None",
                    "Unknown",
                ],
                key=f"function-{i}-DEP-027",
            )

            if (
                function["DEP-027"]
                and not set(function["DEP-027"]).issubset(
                    {"None", "Unknown"}
                )
            ):
                function["DEP-027-details"] = show_details(
                    "Describe the evidence supporting the "
                    "clinical association.",
                    f"function-{i}-DEP-027-details",
                )
            else:
                function["DEP-027-details"] = None

            # DEP-028

            st.markdown(
                "**DEP-028 — Clinical Performance Evidence Type**"
            )

            function["DEP-028"] = st.multiselect(
                "What type of clinical performance evidence exists?",
                [
                    "Retrospective analysis",
                    "Reader study",
                    "Prospective study",
                    "Clinical investigation",
                    "Real-world data",
                    "Literature only",
                    "None yet",
                    "Unknown",
                ],
                key=f"function-{i}-DEP-028",
            )

            # DEP-029 and DEP-030 are conditional if any study
            # type is reported in DEP-028.

            has_reported_study = any(
                item not in ("Unknown", "None yet")
                for item in function["DEP-028"]
            )

            if has_reported_study:

                # DEP-029

                st.markdown(
                    "**DEP-029 — Clinical Study Population and Independence**"
                )

                function["DEP-029-population"] = show_details(
                    "Who was in the clinical study?",
                    f"function-{i}-DEP-029-population",
                    placeholder=(
                        "Describe the study population and "
                        "relevant subgroups."
                    ),
                )

                function["DEP-029-independent"] = yes_no_unknown(
                    "Was the study population independent of the "
                    "data used to develop the product?",
                    f"function-{i}-DEP-029-independent",
                )

                function["DEP-029-relevance"] = show_details(
                    "Describe the relevance of the study population "
                    "to intended clinical practice.",
                    f"function-{i}-DEP-029-relevance",
                )

                # DEP-030

                st.markdown(
                    "**DEP-030 — Clinical Performance Measures and Results**"
                )

                function["DEP-030-measures"] = st.multiselect(
                    "Which clinical performance measures were reported?",
                    [
                        "Sensitivity",
                        "Specificity",
                        "Positive predictive value (PPV)",
                        "Negative predictive value (NPV)",
                        "Likelihood ratios",
                        "Confidence intervals",
                        "Agreement with reference",
                        "Other",
                    ],
                    key=f"function-{i}-DEP-030-measures",
                )

                function["DEP-030-other"] = show_other(
                    function["DEP-030-measures"],
                    f"function-{i}-DEP-030-other",
                )

                function["DEP-030-comparator"] = st.selectbox(
                    "What was the comparator?",
                    [
                        "Select an option",
                        "Standard of care",
                        "Acquired reference",
                        "None",
                    ],
                    key=f"function-{i}-DEP-030-comparator",
                )

                function["DEP-030-results"] = show_details(
                    "Describe the clinical performance results.",
                    f"function-{i}-DEP-030-results",
                )

                function["DEP-030-limitations"] = show_details(
                    "Describe the limitations of the reported results.",
                    f"function-{i}-DEP-030-limitations",
                )

            else:
                function["DEP-029-population"] = None
                function["DEP-029-independent"] = None
                function["DEP-029-relevance"] = None
                function["DEP-030-measures"] = None
                function["DEP-030-other"] = None
                function["DEP-030-comparator"] = None
                function["DEP-030-results"] = None
                function["DEP-030-limitations"] = None

            # DEP-031

            st.markdown("**DEP-031 — Human-AI Team Evaluation**")

            function["DEP-031-trigger"] = st.selectbox(
                "Do users interact with or act on the AI output "
                "according to AIF-016 or AIF-017?",
                [
                    "Select an option",
                    "Yes",
                    "No",
                    "Unknown",
                ],
                key=f"function-{i}-DEP-031-trigger",
            )

            if function["DEP-031-trigger"] == "Yes":

                function["DEP-031"] = st.selectbox(
                    "Was the combined performance of users and the "
                    "AI evaluated?",
                    [
                        "Select an option",
                        "Yes",
                        "No",
                        "Not applicable",
                        "Unknown",
                    ],
                    key=f"function-{i}-DEP-031",
                )

                if function["DEP-031"] == "Yes":
                    function["DEP-031-details"] = show_details(
                        "Describe the evaluation (for example, "
                        "reader study or usability testing).",
                        f"function-{i}-DEP-031-details",
                    )
                elif function["DEP-031"] == "Not applicable":
                    function["DEP-031-details"] = show_details(
                        "Explain why this is not applicable.",
                        f"function-{i}-DEP-031-details",
                    )
                else:
                    function["DEP-031-details"] = None

            else:
                function["DEP-031"] = None
                function["DEP-031-details"] = None

            # DEP-032

            st.markdown(
                "**DEP-032 — Evidence-to-Claim Alignment**"
            )

            function["DEP-032"] = yes_partly_no_unknown(
                "Does the evidence directly support each clinical "
                "application and clinical use claimed?",
                f"function-{i}-DEP-032",
            )

            if function["DEP-032"] in ("Yes", "Partly", "No"):
                function["DEP-032-details"] = show_details(
                    "For each application in PIP-004 and the use "
                    "in PIP-023 / AIF-010, explain how the evidence "
                    "supports the claim.",
                    f"function-{i}-DEP-032-details",
                )
            else:
                function["DEP-032-details"] = None

            # DEP-033

            st.markdown(
                "**DEP-033 — Rationale Where No Device-Specific Clinical Data**"
            )

            if (
                "Literature only" in function["DEP-028"]
                or "None yet" in function["DEP-028"]
            ):
                function["DEP-033"] = show_details(
                    "If there is no device-specific clinical data, "
                    "what rationale shows the available evidence "
                    "is sufficient?",
                    f"function-{i}-DEP-033",
                    height=120,
                    placeholder=(
                        "Provide the rationale using available "
                        "evidence. Enter Unknown if not established."
                    ),
                )
            else:
                function["DEP-033"] = None

            # DEP-034

            st.markdown(
                "**DEP-034 — Planned Human Studies and Authorization**"
            )

            function["DEP-034"] = yes_no_unknown(
                "Is a study on human participants planned or under way?",
                f"function-{i}-DEP-034",
            )

            if function["DEP-034"] == "Yes":

                function["DEP-034-location"] = st.text_input(
                    "Where will the study take place?",
                    key=f"function-{i}-DEP-034-location",
                )

                function["DEP-034-authorization"] = show_details(
                    "What authorization or approval is required, "
                    "and what is its current status?",
                    f"function-{i}-DEP-034-authorization",
                )

            else:
                function["DEP-034-location"] = None
                function["DEP-034-authorization"] = None

        profile["ai_function_versions"].append(function)

    # ========================================================
    # 06 / EVIDENCE DOCUMENTATION
    # DEP-035 TO DEP-036
    # ========================================================

    st.divider()
    st.subheader("06 / Evidence Documentation")

    # DEP-035 — Repeatable Evidence Document Register

    st.markdown("**DEP-035 — Evidence Document Register**")

    st.write(
        "List each document that supports your answers. "
        "Create one record for each supporting document."
    )

    document_count = st.number_input(
        "How many supporting documents are being listed?",
        min_value=1,
        max_value=100,
        value=1,
        step=1,
        key="document-count",
    )

    profile["evidence_documents"] = []

    for i in range(int(document_count)):

        document = {}

        with st.expander(
            f"Supporting Document {i + 1}",
            expanded=(i == 0),
        ):

            document["title"] = st.text_input(
                "Document title",
                key=f"document-{i}-title",
            )

            document["document_id"] = st.text_input(
                "Document ID",
                key=f"document-{i}-id",
            )

            document["version"] = st.text_input(
                "Document version",
                key=f"document-{i}-version",
            )

            document["date"] = st.text_input(
                "Document date",
                placeholder="YYYY-MM-DD or Unknown",
                key=f"document-{i}-date",
            )

            document["page_section"] = st.text_input(
                "Page or section",
                key=f"document-{i}-page-section",
            )

            document["supported_fields"] = st.text_input(
                "DEP field IDs supported by this document",
                placeholder="Example: DEP-001, DEP-005, DEP-014",
                key=f"document-{i}-supported-fields",
            )

        profile["evidence_documents"].append(document)

    # DEP-036 — GMLP

    st.markdown(
        "**DEP-036 — GMLP Implementation Description**"
    )

    profile["DEP-036-trigger"] = st.selectbox(
        "Is a Health Canada or FDA MLMD/AI submission planned?",
        [
            "Select an option",
            "Yes",
            "No",
            "Unknown",
        ],
        key="DEP-036-trigger",
    )

    if profile["DEP-036-trigger"] == "Yes":

        profile["DEP-036"] = st.selectbox(
            "Has the developer documented how Good Machine Learning "
            "Practice (GMLP) principles were considered across "
            "development and testing?",
            [
                "Select an option",
                "Yes",
                "Partly",
                "No",
                "Unknown",
            ],
            key="DEP-036",
        )

        if profile["DEP-036"] in ("Yes", "Partly"):
            profile["DEP-036-document"] = st.text_input(
                "Reference the document that describes GMLP implementation.",
                key="DEP-036-document",
            )
        else:
            profile["DEP-036-document"] = None

    else:
        profile["DEP-036"] = None
        profile["DEP-036-document"] = None

    # ========================================================
    # RETURN ALL ANSWERS
    # ========================================================

    return profile
