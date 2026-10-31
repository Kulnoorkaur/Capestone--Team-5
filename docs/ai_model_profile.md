# AI Model Profile

## 1. Overview

The AI Model Profile is the first component of the AI Regulatory Readiness Platform. It collects information about an AI-enabled medical device to support preliminary regulatory screening and readiness assessments.

The information entered by the user will help the platform understand the device's intended purpose, clinical application, functionality, and role in clinical decision-making.

The profile will serve as a common source of information for the different regulatory assessments, reducing the need for users to repeatedly enter the same information.

## 2. Proposed Profile Fields

The following table outlines the initial information that the platform is expected to collect.

| Category               | Field                       | Description                                                                             |
| ---------------------- | --------------------------- | --------------------------------------------------------------------------------------- |
| Product Information    | Product Name                | Name of the AI system being assessed                                                    |
| Product Information    | Product Description         | Brief description of what the system does                                               |
| Intended Use           | Intended Medical Purpose    | Medical purpose or clinical problem the system is intended to address                   |
| Intended Use           | Target Patient Population   | Patient population the system is intended for                                           |
| Intended Use           | Intended Users              | Healthcare professionals or other users expected to operate the system                  |
| Intended Use           | Clinical Setting            | Environment where the system will be used                                               |
| AI Functionality       | AI Function                 | Main function of the AI system, such as detection, diagnosis, prediction, or monitoring |
| AI Functionality       | Input Data                  | Type of data processed by the AI system, such as CT, MRI, or X-ray images               |
| AI Functionality       | Output                      | Results or information produced by the AI system                                        |
| Clinical Role          | Clinical Decision Supported | Clinical decision or task supported by the AI output                                    |
| Clinical Role          | Level of Automation         | Extent to which the system operates independently or requires human involvement         |
| Clinical Role          | Human Oversight             | How healthcare professionals review, interpret, or act on the AI output                 |
| Regulatory Information | Target Jurisdictions        | Countries or regions where the device is intended to be marketed                        |
| Regulatory Information | Development Stage           | Current stage of development, such as concept, prototype, validation, or market-ready   |

## 3. Use of Profile Information

The information collected through the AI Model Profile will be used to support the following platform components.

### Preliminary Regulatory Screening

Profile information will help identify potentially applicable medical device regulations, preliminary classifications, and regulatory pathways.

For example, the intended medical purpose, AI functionality, and role in clinical decision-making may influence whether the software is considered a medical device and which regulatory requirements apply.

### Stage-Gated Readiness Assessment

The profile will provide context for the readiness assessment by identifying the AI system's intended use, functionality, and development stage.

This will help determine which assessment criteria are relevant to the system.

### Documentation Tracking and Roadmap

The profile will also help identify documentation that may be needed and provide context for recommended next steps.

## 4. Example AI Model Profile

The following example illustrates how the profile could be completed for a hypothetical AI-enabled medical imaging system.

| Field                       | Example                                                                   |
| --------------------------- | ------------------------------------------------------------------------- |
| Product Name                | Lung Nodule Detection AI                                                  |
| Product Description         | Software that analyzes chest CT images to identify potential lung nodules |
| Intended Medical Purpose    | Assist radiologists in identifying potential lung nodules                 |
| Target Patient Population   | Adults undergoing chest CT examinations                                   |
| Intended Users              | Radiologists                                                              |
| Clinical Setting            | Hospital radiology departments                                            |
| AI Function                 | Detection                                                                 |
| Input Data                  | Chest CT images                                                           |
| Output                      | Highlighted regions indicating potential lung nodules                     |
| Clinical Decision Supported | Review and interpretation of chest CT images                              |
| Level of Automation         | AI-assisted detection with radiologist review                             |
| Human Oversight             | Radiologist reviews AI findings before making clinical decisions          |
| Target Jurisdictions        | Canada, United States, European Union                                     |
| Development Stage           | Prototype                                                                 |

This example is intended to demonstrate the type of information collected and does not represent a completed regulatory assessment.

## 5. Development Considerations

The profile structure is preliminary and may be updated as regulatory requirements and platform specifications are further developed.

Additional work will be needed to determine:

* Which fields are required or optional.
* Appropriate input formats, such as text fields, dropdown menus, or multiple-choice selections.
* How incomplete or unclear information will be handled.
* How profile information will be stored and updated.
* How individual fields will connect to regulatory screening and readiness assessment criteria.

These decisions will be refined during platform development and testing.
