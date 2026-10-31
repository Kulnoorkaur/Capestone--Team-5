# System Architecture

## 1. Overview

The AI Regulatory Readiness Platform is being designed to help developers of AI-enabled medical imaging technologies assess their regulatory readiness and identify potential regulatory requirements.

The proposed platform consists of five main components that work together to collect information about an AI system, provide preliminary regulatory screening, assess readiness, track documentation, and identify recommended next steps.

The architecture is still being developed and may change as the team evaluates different technical approaches.

## 2. Proposed System Workflow

The platform is organized around the following workflow:

**AI Model Profile → Preliminary Regulatory Screening → Stage-Gated Readiness Assessment → Documentation Tracking → Personalized Regulatory Roadmap**

Each component uses information collected or generated in previous stages to support the overall assessment.

## 3. Main System Components

### 3.1 AI Model Profile

The AI Model Profile collects information about the user's AI system, including:

* Intended medical purpose
* Clinical application and setting
* Target users and patient population
* AI functionality and outputs
* Level of automation and role in clinical decision-making
* Target regulatory jurisdictions

This information provides the starting point for the regulatory screening and readiness assessments.

### 3.2 Preliminary Regulatory Screening

This component uses information from the AI Model Profile to identify potentially applicable regulatory requirements.

The screening is intended to help determine:

* Whether the software may qualify as a medical device
* Potential device classification
* Possible regulatory pathways
* Areas requiring further regulatory review

Screening results will be preliminary and may require manual verification, particularly when regulatory requirements are unclear or depend on additional information.

### 3.3 Stage-Gated Readiness Assessment

The readiness assessment evaluates whether the AI system has addressed key regulatory development requirements.

The proposed assessment covers ten areas:

1. Intended purpose and product definition
2. Preliminary regulatory classification and pathway
3. Dataset readiness
4. Technical risk management
5. Technical performance and validation
6. Clinical evidence
7. Cybersecurity and information for use
8. Change management and lifecycle planning
9. Post-market monitoring
10. Documentation completeness and traceability

Each gate will include assessment criteria to help identify completed requirements, missing information, and areas requiring additional work.

### 3.4 Documentation Tracking

This component is intended to help users organize and track the documentation needed to support regulatory readiness.

It will identify:

* Available supporting documentation
* Missing or incomplete evidence
* Requirements that still need to be addressed

The documentation tracking system will be connected to the readiness assessment so users can identify which requirements need further attention.

### 3.5 Personalized Regulatory Roadmap

The roadmap will summarize the results of the regulatory screening and readiness assessment.

It is intended to provide:

* An overview of the AI system's current regulatory readiness
* Areas requiring additional work
* Recommended next steps
* Items requiring further review or clarification

The roadmap will help users understand what they may need to address as they continue developing their AI system.

## 4. Technical Implementation

The technical implementation is still being evaluated.

The team is considering different approaches for developing the user interface, regulatory screening logic, readiness assessments, and data management.

The selected approach will need to support:

* Consistent application of regulatory requirements
* Traceability between assessment results and regulatory sources
* Clear identification of missing information and uncertain results
* Updates to regulatory requirements as guidance changes
* Testing and validation of platform outputs

Specific technologies and implementation methods will be documented as development progresses.

## 5. Current Development Status

The project is currently in the system design and early development stage.

Current work includes defining the platform components, developing the AI Model Profile structure, organizing regulatory requirements, and establishing assessment criteria.

The architecture will be updated as technical decisions are finalized and the initial prototype is developed.
