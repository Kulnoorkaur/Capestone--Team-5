"""
Questionnaire Bridge
--------------------
Connects the Gemini Chat Buddy to the structured
Deliverable 2 questionnaires.

Supported questionnaires:
- D2.1 Product and Intended-Use Profile
- D2.2 AI Function and Clinical Workflow

The bridge validates confirmed answers and preserves
the original questionnaire field identifiers.

The existing D2.1 interface remains backward-compatible.
"""

from importlib import import_module


# ============================================================
# D2.1 FIELD DEFINITIONS
# ============================================================

D21_MULTISELECT_FIELDS = {
    "PIP-007": [
        "Radiologist",
        "Physician",
        "Technologist",
        "Nurse",
        "Other healthcare professional",
        "Patient",
        "Caregiver",
        "Other",
    ],
    "PIP-016": [
        "Hospital",
        "Outpatient clinic",
        "Diagnostic imaging centre",
        "Emergency department",
        "Home",
        "Other",
    ],
    "PIP-022": [
        "Image analysis",
        "Detection",
        "Classification",
        "Segmentation",
        "Quantification",
        "Prediction",
        "Other",
    ],
}

D21_SELECTBOX_FIELDS = {
    "PIP-006": [
        "CT",
        "MRI",
        "X-ray",
        "Ultrasound",
        "PET",
        "Other",
    ],
    "PIP-008": [
        "Healthcare professional only",
        "Patient or caregiver",
        "Both",
    ],
    "PIP-009": [
        "Yes",
        "No",
        "Unknown",
    ],
    "PIP-017": [
        "Screening",
        "Diagnosis",
        "Monitoring",
        "Treatment planning",
        "Follow-up",
        "Other",
    ],
    "PIP-018": [
        "Routine",
        "Time-critical",
        "Both",
        "Unknown",
    ],
}

D21_TEXT_FIELDS = {
    "PIP-001",
    "PIP-002",
    "PIP-003",
    "PIP-004",
    "PIP-005",
    "PIP-010",
    "PIP-011",
    "PIP-012",
    "PIP-013",
    "PIP-014",
    "PIP-015",
    "PIP-019",
    "PIP-020",
    "PIP-021",
    "PIP-023",
    "PIP-024",
}

D21_CONDITIONAL_FIELDS = {
    "PIP-006-OTHER": ("PIP-006", "Other"),
    "PIP-007-OTHER": ("PIP-007", "Other"),
    "PIP-016-OTHER": ("PIP-016", "Other"),
    "PIP-017-OTHER": ("PIP-017", "Other"),
    "PIP-022-OTHER": ("PIP-022", "Other"),
    "TRAINING-DETAILS": ("PIP-009", "Yes"),
}


# ============================================================
# D2.2 FIELD DEFINITIONS
# ============================================================

D22_MULTISELECT_FIELDS = {
    "AIF-001": [
        "Medical images",
        "Image-derived measurements",
        "Clinical metadata",
        "Other",
    ],
    "AIF-003": [
        "Scanner",
        "PACS",
        "EHR",
        "User upload",
        "Other",
    ],
    "AIF-006": [
        "Label",
        "Probability",
        "Score",
        "Alert",
        "Measurement",
        "Segmentation",
        "Transformed image",
        "Recommendation",
        "Other",
    ],
    "AIF-007": [
        "Image overlay",
        "Report",
        "Dashboard",
        "PACS",
        "EHR",
        "Notification",
        "API",
        "Other",
    ],
    "AIF-009": [
        "Thresholds",
        "Confidence or uncertainty",
        "Explanations",
        "Warnings or limitations",
        "None",
        "Unknown",
        "Other",
    ],
    "AIF-012": [
        "Clinical review",
        "Referral",
        "Additional workup",
        "Treatment",
        "No action",
        "Other",
    ],
    "AIF-018": [
        "Disregard",
        "Correct",
        "Override",
        "Stop",
        "None",
        "Other",
    ],
    "AIF-020": [
        "Reject input",
        "Flag issue",
        "Withhold result",
        "Request human review",
        "Unknown",
        "Other",
    ],
}

D22_SELECTBOX_FIELDS = {
    "AIF-005": [
        "Yes",
        "No",
        "Unknown",
    ],
    "AIF-014": [
        "Yes",
        "No",
        "Sometimes",
        "Unknown",
    ],
    "AIF-016": [
        "Always",
        "Sometimes",
        "Never",
        "Unknown",
    ],
    "AIF-017": [
        "Yes",
        "Partly",
        "No",
        "Unknown",
    ],
    "AIF-019": [
        "Yes",
        "No",
        "Unknown",
    ],
}

D22_TEXT_FIELDS = {
    "AIF-002",
    "AIF-004",
    "AIF-008",
    "AIF-010",
    "AIF-011",
    "AIF-013",
    "AIF-015",
}

D22_CONDITIONAL_FIELDS = {
    "AIF-001-OTHER": ("AIF-001", "Other"),
    "AIF-003-OTHER": ("AIF-003", "Other"),
    "AIF-006-OTHER": ("AIF-006", "Other"),
    "AIF-007-OTHER": ("AIF-007", "Other"),
    "AIF-009-OTHER": ("AIF-009", "Other"),
    "AIF-012-OTHER": ("AIF-012", "Other"),
    "AIF-018-OTHER": ("AIF-018", "Other"),
    "AIF-020-OTHER": ("AIF-020", "Other"),

    "AIF-005-DETAILS": ("AIF-005", "Yes"),
    "AIF-014-DETAILS": ("AIF-014", ("Yes", "Sometimes")),
    "AIF-016-DETAILS": (
        "AIF-016",
        ("Always", "Sometimes", "Never"),
    ),
    "AIF-017-DETAILS": (
        "AIF-017",
        ("Yes", "Partly", "No"),
    ),
    "AIF-019-DETAILS": ("AIF-019", "Yes"),
}


# ============================================================
# COMBINED FIELD DEFINITIONS
# ============================================================

MULTISELECT_FIELDS = {
    **D21_MULTISELECT_FIELDS,
    **D22_MULTISELECT_FIELDS,
}

SELECTBOX_FIELDS = {
    **D21_SELECTBOX_FIELDS,
    **D22_SELECTBOX_FIELDS,
}

TEXT_FIELDS = D21_TEXT_FIELDS | D22_TEXT_FIELDS

CONDITIONAL_FIELDS = {
    **D21_CONDITIONAL_FIELDS,
    **D22_CONDITIONAL_FIELDS,
}

QUESTIONNAIRE_FIELDS = {
    "D2.1": [
        f"PIP-{number:03d}"
        for number in range(1, 25)
    ],
    "D2.2": [
        f"AIF-{number:03d}"
        for number in range(1, 21)
    ],
}

CONDITIONAL_LABELS = {
    "AIF-005-DETAILS": (
        "Describe the image modification or generated image "
        "and whether the original image is retained."
    ),
    "AIF-014-DETAILS": (
        "Describe what additional clinical confirmation "
        "is required and when it occurs."
    ),
    "AIF-016-DETAILS": (
        "Describe the professional review and clinical "
        "action sequence."
    ),
    "AIF-017-DETAILS": (
        "Describe the information available for "
        "independent assessment of the AI output."
    ),
    "AIF-019-DETAILS": (
        "Describe actions initiated without human "
        "approval, including triggers and safeguards."
    ),
}

for field_id in D22_CONDITIONAL_FIELDS:
    if field_id.endswith("-OTHER"):
        CONDITIONAL_LABELS[field_id] = (
            "Please specify the other option."
        )


# ============================================================
# QUESTIONNAIRE BRIDGE
# ============================================================

class QuestionnaireBridge:

    def __init__(self):
        self.field_labels = self._load_field_labels()
        self.answers = {}

    def _load_field_labels(self):
        """
        Reuse labels from the team's existing questionnaires.
        """

        product_module = import_module(
            "app.deliverable_2.questionnaires.product_profile"
        )

        ai_module = import_module(
            "app.deliverable_2.questionnaires.ai_function"
        )

        labels = dict(product_module.FIELD_LABELS)

        labels.update(ai_module.FIELD_LABELS)

        labels.update(CONDITIONAL_LABELS)

        return labels

    def get_field_label(self, field_id):
        return self.field_labels.get(field_id, field_id)

    def get_field_type(self, field_id):

        if field_id in MULTISELECT_FIELDS:
            return "multiselect"

        if field_id in SELECTBOX_FIELDS:
            return "selectbox"

        if field_id in TEXT_FIELDS:
            return "text"

        if field_id in CONDITIONAL_FIELDS:
            return "text"

        return None

    def get_field_options(self, field_id):

        if field_id in MULTISELECT_FIELDS:
            return MULTISELECT_FIELDS[field_id]

        if field_id in SELECTBOX_FIELDS:
            return SELECTBOX_FIELDS[field_id]

        return None

    def validate_answer(self, field_id, value):
        """
        Validate an answer against its accepted
        questionnaire data type and options.
        """

        field_type = self.get_field_type(field_id)

        if field_type is None:
            return False, "Unknown questionnaire field."

        if field_type == "text":

            if not isinstance(value, str):
                return False, "This field requires text."

            if not value.strip():
                return False, "The answer cannot be empty."

            return True, None

        if field_type == "selectbox":

            if not isinstance(value, str):
                return False, "This field requires a dropdown option."

            if value not in SELECTBOX_FIELDS[field_id]:
                return False, "Invalid dropdown option."

            return True, None

        if field_type == "multiselect":

            if not isinstance(value, list):
                return False, "This field requires a list."

            allowed = MULTISELECT_FIELDS[field_id]

            if not value or any(
                item not in allowed for item in value
            ):
                return False, "Invalid multiselect option."

            return True, None

        return False, "Unsupported field type."

    def _condition_matches(self, value, trigger):
        """
        Determine whether a conditional question
        should be active.
        """

        if value is None:
            return False

        if isinstance(trigger, tuple):
            triggers = trigger
        else:
            triggers = (trigger,)

        if isinstance(value, list):
            return any(item in triggers for item in value)

        return value in triggers

    def save_answer(self, field_id, value):
        """
        Save a validated, user-confirmed answer.
        """

        valid, error = self.validate_answer(field_id, value)

        if not valid:
            return False, error

        # Prevent saving an inactive conditional answer.
        if field_id in CONDITIONAL_FIELDS:

            parent_id, trigger = CONDITIONAL_FIELDS[field_id]

            parent_value = self.answers.get(parent_id)

            if not self._condition_matches(parent_value, trigger):
                return (
                    False,
                    "This conditional question is not currently active.",
                )

        self.answers[field_id] = value

        # Remove conditional answers that no longer apply.
        for child_id, (parent_id, trigger) in CONDITIONAL_FIELDS.items():

            if parent_id != field_id:
                continue

            if not self._condition_matches(value, trigger):
                self.answers.pop(child_id, None)

        return True, None

    def get_missing_fields(self, questionnaire="D2.1"):
        """
        Return unanswered primary fields for a questionnaire.

        Defaults to D2.1 for compatibility with the
        existing Chat Buddy.
        """

        if questionnaire not in QUESTIONNAIRE_FIELDS:
            raise ValueError(
                f"Unsupported questionnaire: {questionnaire}"
            )

        return [
            field_id
            for field_id in QUESTIONNAIRE_FIELDS[questionnaire]
            if field_id not in self.answers
        ]

    def get_active_conditional_fields(self, questionnaire="D2.1"):
        """
        Return active conditional fields.

        Defaults to D2.1 for compatibility with the
        existing Chat Buddy.
        """

        if questionnaire not in QUESTIONNAIRE_FIELDS:
            raise ValueError(
                f"Unsupported questionnaire: {questionnaire}"
            )

        prefix = (
            "PIP-"
            if questionnaire == "D2.1"
            else "AIF-"
        )

        active = []

        for field_id, (parent_id, trigger) in CONDITIONAL_FIELDS.items():

            if not (
                field_id.startswith(prefix)
                or (
                    questionnaire == "D2.1"
                    and field_id == "TRAINING-DETAILS"
                )
            ):
                continue

            value = self.answers.get(parent_id)

            if self._condition_matches(value, trigger):
                active.append(field_id)

        return active

    def get_questionnaire_answers(self, questionnaire):
        """
        Return confirmed answers belonging to
        one questionnaire.
        """

        if questionnaire not in QUESTIONNAIRE_FIELDS:
            raise ValueError(
                f"Unsupported questionnaire: {questionnaire}"
            )

        primary_fields = set(
            QUESTIONNAIRE_FIELDS[questionnaire]
        )

        conditional_fields = set(
            self.get_active_conditional_fields(questionnaire)
        )

        allowed_fields = primary_fields | conditional_fields

        return {
            field_id: value
            for field_id, value in self.answers.items()
            if field_id in allowed_fields
        }

    def get_questionnaire_progress(self, questionnaire):
        """
        Return primary-field completion statistics.
        """

        if questionnaire not in QUESTIONNAIRE_FIELDS:
            raise ValueError(
                f"Unsupported questionnaire: {questionnaire}"
            )

        fields = QUESTIONNAIRE_FIELDS[questionnaire]

        completed = sum(
            field_id in self.answers
            for field_id in fields
        )

        return {
            "completed": completed,
            "total": len(fields),
            "remaining": len(fields) - completed,
        }

    def get_product_profile(self):
        """
        Return a copy of all confirmed questionnaire answers.

        Preserves the existing method's behavior.
        """

        return dict(self.answers)