# Deliverable 2 – AI Model Profile

This folder contains the questionnaires and preliminary validation code for the AI Model Profile.

## Questionnaires

Located in `questionnaires/`

- **product_profile.py** – D2.1 questionnaire for product identification and intended use.
- **ai_function.py** – D2.2 questionnaire for AI inputs, outputs, clinical workflow, and automation.
- **Dataset_&_evidence_profile.py** – Questionnaire for dataset and evidence information.

These files contain the questions and collect user responses.

## Validation

Located in `validation/`

- **run_product_profile.py** – Runs the D2.1 questionnaire, validates responses, displays a profile summary, and allows JSON export.
- **run_ai_function.py** – Runs the D2.2 questionnaire, validates responses, displays a profile summary, and allows JSON export.

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
