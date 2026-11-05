# Deliverable 2: AI Model Profile and Regulatory Pathway Identification

## Overview

Deliverable 2 focuses on developing the **AI Model Profile**, which is the starting point for our AI Regulatory Readiness Platform.

Before the platform can assess regulatory readiness, it needs to understand the AI product being evaluated. This includes its intended purpose, AI functionality, clinical workflow, and how clinicians interact with its outputs.

To collect this information, we are developing structured questionnaires covering different aspects of an AI-enabled medical imaging product.

The responses will eventually be combined into a single AI Model Profile that can be used for preliminary regulatory screening and stage-gated readiness assessments.

## How It Works

The current development process involves the following steps:

### 1. Questionnaire Development

Each questionnaire focuses on a different aspect of the AI product.

Users will answer questions about their product's intended use, functionality, clinical workflow, and other relevant characteristics.

Each question is assigned a unique identifier (e.g., `AIF-001`) to make it easier to organize responses and reference specific information throughout the platform.

### 2. Response Collection

The questionnaires are being developed using Python and Streamlit.

Responses are collected in a structured format so they can eventually be combined into a single AI Model Profile.

Currently, the questionnaires are being developed and tested individually before being integrated into the main platform.

### 3. Questionnaire Validation

Validation functions are being developed to check the quality and completeness of the collected information.

Depending on the questionnaire, these checks may identify:

- Missing required responses.
- Incomplete explanations.
- Responses requiring additional clarification.
- Potential inconsistencies between answers.
- Information that may require manual review.

The purpose of validation is to ensure that the information collected is sufficiently complete and clear for further assessment.

**Questionnaire validation does not determine whether a product meets regulatory requirements or passes a readiness gate.**

### 4. Future Integration

Once the questionnaires and validation functions are developed, the next step will be to integrate them into a single AI Model Profile.

The collected information will eventually support:

- **Preliminary Regulatory Screening:** Identifying potentially applicable regulatory frameworks, classifications, and pathways.
- **Stage-Gated Readiness Assessment:** Evaluating the product against specific readiness criteria and identifying gaps in evidence or documentation.
- **Documentation Tracking:** Identifying and organizing documentation needed for regulatory planning.
- **Personalized Roadmap:** Providing guidance on areas requiring further development or review.

These components are part of the broader platform and are not fully implemented in the current Deliverable 2 code.

## Deliverable 2 Components

Deliverable 2 is divided into five sections:

| Section | Description |
|---|---|
| **2.1 Product and Intended Use** | Collects information about the product's intended purpose, target users, patient population, and clinical setting. |
| **2.2 AI Function and Clinical Workflow** | Collects information about AI inputs, processing, outputs, clinical workflow, and clinician interaction. |
| **2.3 CDS vs. Automation** | Examines the AI system's role in clinical decision-making and the level of human involvement. |
| **2.4 Jurisdiction-Specific Regulatory Logic** | Develops preliminary screening logic for identifying potentially applicable regulatory frameworks and pathways. |
| **2.5 Data Dictionary** | Defines questionnaire fields, identifiers, response formats, and data structures. |

The individual components are being developed separately before integration.

## Code Organization

The code is organized into separate folders for questionnaires and validation.

### Questionnaires

The `questionnaires/` folder contains the code used to display questions and collect user responses through Streamlit.

Each questionnaire focuses on a specific area of the AI Model Profile.

For example, `ai_function.py` collects information about how the AI processes inputs, generates outputs, and interacts with clinicians.

### Validation

The `validation/` folder contains supporting code for running and checking questionnaire responses.

The runner files allow individual questionnaires to be launched and tested.

The validation functions check responses for completeness, consistency, and potential issues requiring clarification.

Some questionnaire fields may also be mapped to relevant readiness gates to support future integration. However, **these mappings do not currently perform gate assessments or determine regulatory readiness.**

## Current Development Approach

We are currently using **Python and Streamlit** to develop the questionnaires and preliminary interface.

Our immediate focus is on:

- Developing the individual questionnaires.
- Collecting and organizing user responses.
- Implementing questionnaire validation.
- Standardizing field identifiers and response formats.
- Preparing the questionnaires for integration into a single AI Model Profile.

The final data storage approach and regulatory screening implementation are still being determined.

## Connection to the Overall Platform

Deliverable 2 provides the information that will be used by other components of the platform.

The proposed workflow is:

```text
AI Model Profile
       ↓
Preliminary Regulatory Screening
       ↓
Stage-Gated Readiness Assessment
       ↓
Documentation Tracking
       ↓
Personalized Regulatory Roadmap
```

The questionnaires developed in Deliverable 2 will provide the initial product information.

Preliminary regulatory screening will use this information to identify potentially applicable regulatory considerations, while the stage-gated assessment developed in Deliverable 3 will evaluate readiness against specific criteria.

Although some questionnaire fields may already be associated with relevant gates, the current code does not yet implement the full regulatory screening or readiness assessment logic.

## Current Status

**Status: In Progress**

The team is currently developing and testing the individual questionnaires and supporting validation functions.

The next steps include integrating the questionnaires, standardizing how responses are stored, and connecting the collected information to the preliminary regulatory screening and stage-gated readiness components.

The platform is intended to support early regulatory planning and identify areas requiring further review. It will not provide final regulatory classifications or replace professional regulatory assessment.
