# Questionnaires

## Overview

This folder contains the questionnaires being developed for the **AI Regulatory Readiness Platform for Imaging-Informed AI**.

The questionnaires are based on Deliverable 2 (AI Model Profile) and are intended to collect information about an imaging-AI product, including its intended use, AI functionality, algorithm characteristics, datasets, and risk-related considerations.

The information collected will support preliminary regulatory screening and stage-gated readiness assessments. The goal is to provide a structured way for developers to describe their products and identify information that may be needed for regulatory planning.

## Questionnaire Sections

The questionnaires are organized according to the Deliverable 2 mini-deliverables:

| Deliverable | Questionnaire Section |
|---|---|
| D2.1 | Product Identification and Intended Use |
| D2.2 | AI Function and Clinical Workflow |
| D2.3 | Algorithm Characteristics and Change Control |
| D2.4 | Dataset and Evidence |
| D2.5 | Risk, Cybersecurity, and Documentation |

Each section focuses on a different aspect of the AI product. The questionnaires will initially be developed as separate components before being integrated into the main application.

Overlapping questions and shared information will be reviewed during integration to avoid asking users for the same information multiple times.

## Planned Functionality

The questionnaires are intended to:

- Collect product information through an interactive interface.
- Use structured response fields, including dropdown menus, multiple-choice selections, and text inputs.
- Display additional questions when certain responses require further explanation.
- Identify missing, incomplete, uncertain, or conflicting information.
- Store questionnaire responses in a structured format.
- Connect relevant responses to preliminary regulatory screening and readiness gates.
- Allow supporting evidence or documentation references to be recorded where applicable.

The questionnaires are designed to collect and organize product information. They will not independently determine regulatory classification, compliance, or approval status.

## Technical Approach

The technical implementation is still being developed, and some technology choices have not been finalized.

The current prototype uses **Python and Streamlit** to develop the questionnaire interface and collect structured product information.

The following approaches are being considered:

| Technology or Approach | Current Status |
|---|---|
| Python | Currently used for prototype development |
| Streamlit | Currently used for the interface |
| JSON | Proposed format for storing questionnaire responses |
| SQLite | Possible option for future data storage |
| Rule-based logic | Being considered for preliminary regulatory screening |
| Large Language Model (LLM) | Potential use under consideration; specific role not yet determined |

The team is considering a rule-based approach in which questionnaire responses are evaluated using predefined regulatory criteria. The potential use of an LLM has not been ruled out, but its purpose and implementation have not yet been decided.

Any proposed LLM functionality would need to be evaluated for reliability, transparency, traceability, and suitability for regulatory assessments.

For now, the questionnaires are being developed separately from the regulatory decision logic so that they can be adapted as the platform's technical approach is finalized.

## Development and Integration

Each questionnaire section will be developed and tested individually before being integrated into the main platform.

During integration, the team will review:

- Potential overlaps between questionnaire sections.
- Field IDs, definitions, and response formats.
- Required and conditional questions.
- Handling of missing or uncertain information.
- Storage and retrieval of questionnaire responses.
- Connections between questionnaire fields, regulatory requirements, and readiness gates.

The collected information is intended to support three main platform components:

**1. Preliminary Regulatory Screening**

Questionnaire responses will provide information needed to assess potential medical-device status, preliminary classification, and applicable regulatory pathways across the selected jurisdictions.

**2. Stage-Gated Readiness Assessment**

Relevant questionnaire fields will be linked to readiness gates to help identify information, evidence, and documentation gaps.

**3. Documentation Tracking and Roadmap**

The platform will use information from the profile and readiness assessments to help organize outstanding requirements and identify possible next steps for regulatory planning.

Regulatory decision logic and readiness assessments will be developed separately and integrated with the questionnaires as the project progresses.

## Testing and Validation

The questionnaires will be tested using representative imaging-AI product scenarios to evaluate whether they collect the necessary information and function as intended.

Testing may include:

- Clinician-reviewed AI detection or diagnostic support.
- Automated triage or prioritization.
- Basic image display or transfer functions.
- Products with multiple AI functions.
- Missing, uncertain, or contradictory responses.

Testing will focus on questionnaire functionality, response handling, and consistency of collected information.

The team will also review whether the questions are understandable, whether important information is missing, and whether responses can be used by the regulatory screening and readiness assessment components.

## Current Status

The questionnaires are currently under development.

Initial work focuses on implementing the Deliverable 2 fields, creating the user interface, collecting structured responses, and testing basic functionality.

Field definitions, validation rules, storage methods, and integration approaches may change as development continues.

The final technical architecture, including the potential use of an LLM, has not yet been determined.
