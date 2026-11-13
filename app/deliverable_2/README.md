# Deliverable 2 – AI Model Profile

This folder contains the questionnaires and preliminary validation code for the AI Model Profile.

## Questionnaires

Located in `questionnaires/`

- **product_profile.py** – D2.1 questionnaire for product identification and intended use.
- **ai_function.py** – D2.2 questionnaire for AI inputs, outputs, clinical workflow, and automation.
- **Dataset_&_evidence_profile.py** – Questionnaire for dataset and evidence information.
- **risk_documentation.py** – D2.5 questionnaire for product-related risks, risk controls, cybersecurity measures, user information, and existing regulatory documentation.

These files contain the questions and collect user responses.

## Validation

Located in `validation/`

- **run_product_profile.py** – Runs the D2.1 questionnaire, validates responses, displays a profile summary, and allows JSON export.
- **run_ai_function.py** – Runs the D2.2 questionnaire, validates responses, displays a profile summary, and allows JSON export.
- **run_risk_documentation.py** – Runs the D2.5 questionnaire, validates responses, displays a profile summary, and allows JSON export.

The validation checks identify missing, uncertain, or inconsistent information. They do not determine regulatory classification or readiness.

## How to Run (GitHub Codespaces)

1. Open the repository in GitHub Codespaces.
2. Open the terminal and make sure you are in the main project folder.
3. Run the command for the questionnaire you want to open.

**D2.1 – Product Profile**
```bash
PYTHONPATH=. python -m streamlit run app/deliverable_2/validation/run_product_profile.py
```

**D2.2 – AI Function and Clinical Workflow**
```bash
PYTHONPATH=. python -m streamlit run app/deliverable_2/validation/run_ai_function.py
```

4. Open the forwarded Streamlit port (usually 8501) when prompted to view the questionnaire.

## Development Status

The questionnaires are currently being developed and tested separately before being integrated into the complete AI Model Profile.


## Deliverable 2.6 – Integrated Imaging-AI Product Profile

**Integration Lead:** Chandrima Podder

### Overview
Deliverable 2.6 integrates the five questionnaire components (D2.1–D2.5) into a unified Imaging-AI Product Profile V1.

The integration provides four framework-specific regulatory decision-tree structures:
- Health Canada
- FDA
- EU MDR
- EU AI Act

The integrated framework uses the Deliverable 1.6 Regulatory Requirements Matrix to maintain traceability between questionnaire fields, regulatory requirements, source references, and readiness gates.

### Implementation
The integration is implemented in:

`app/deliverable_2/integration/run_integrated_profile.py`

The application integrates:
- D2.1 – Product and Intended-Use Profile
- D2.2 – AI Function and Clinical Workflow
- D2.3 – Algorithm and Change Control
- D2.4 – Dataset and Evidence
- D2.5 – Risk, Cybersecurity, and Documentation

### Running the Integrated Application

From the repository root:

```bash
python -m pip install -r app/deliverable_2/questionnaires/requirements.txt
python -m streamlit run app/deliverable_2/integration/run_integrated_profile.py
```

### Outputs
The integrated application provides:
- Consolidated product-profile responses (JSON)
- Four regulatory decision-tree assessments and issue log (JSON)
- Integrated field dictionary (CSV)
- Regulatory requirements traceability crosswalk (CSV)

Missing, uncertain, and conflicting information is flagged for manual regulatory review.

### Limitations
This is a preliminary regulatory research and decision-support framework, not a validated regulatory classification or compliance assessment tool.

Decision-tree outcomes, regulatory source mappings, and proposed integration fields require further team review and regulatory verification before finalization.

