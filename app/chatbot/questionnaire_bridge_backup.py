"""
Questionnaire Bridge
--------------------
Connects the Gemini Chat Buddy to the structured
Deliverable 2 questionnaires.

Initial implementation: D2.1 Product and Intended-Use Profile.
"""

from importlib import import_module


# ------------------------------------------------------------
# D2.1 FIELD DEFINITIONS
# ------------------------------------------------------------

# These fields use Streamlit multiselect widgets.
MULTISELECT_FIELDS = {
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


# These fields use Streamlit selectbox widgets.
SELECTBOX_FIELDS = {
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


# These fields accept free-text answers.
TEXT_FIELDS = {
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


# Additional fields appear conditionally.
CONDITIONAL_FIELDS = {
    "PIP-006-OTHER": ("PIP-006", "Other"),
    "PIP-007-OTHER": ("PIP-007", "Other"),
    "PIP-016-OTHER": ("PIP-016", "Other"),
    "PIP-017-OTHER": ("PIP-017", "Other"),
    "PIP-022-OTHER": ("PIP-022", "Other"),
    "TRAINING-DETAILS": ("PIP-009", "Yes"),
}


# ------------------------------------------------------------
# QUESTIONNAIRE BRIDGE
# ------------------------------------------------------------

class QuestionnaireBridge:

    def __init__(self):
        self.field_labels = self._load_field_labels()
        self.answers = {}

    def _load_field_labels(self):
        """
        Reuse the labels defined in the existing D2.1 module.
        """

        module = import_module(
            "app.deliverable_2.questionnaires.product_profile"
        )

        return module.FIELD_LABELS

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
        Validate an answer against the questionnaire's
        accepted data types and options.
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

    def save_answer(self, field_id, value):
        """
        Save a validated answer.

        Only call this after the user confirms the answer.
        """

        valid, error = self.validate_answer(field_id, value)

        if not valid:
            return False, error

        self.answers[field_id] = value

        # Remove conditional answers that no longer apply.
        for child_id, (parent_id, trigger) in CONDITIONAL_FIELDS.items():

            if parent_id != field_id:
                continue

            selected = (
                trigger in value
                if isinstance(value, list)
                else value == trigger
            )

            if not selected:
                self.answers.pop(child_id, None)

        return True, None

    def get_missing_fields(self):
        """
        Return unanswered primary D2.1 fields.
        """

        return [
            field_id
            for field_id in self.field_labels
            if field_id not in self.answers
        ]

    def get_active_conditional_fields(self):
        """
        Return conditional fields activated by saved answers.
        """

        active = []

        for field_id, (parent_id, trigger) in CONDITIONAL_FIELDS.items():

            value = self.answers.get(parent_id)

            selected = (
                trigger in value
                if isinstance(value, list)
                else value == trigger
            )

            if selected:
                active.append(field_id)

        return active

    def get_product_profile(self):
        """
        Return a copy of the confirmed questionnaire answers.
        """

        return dict(self.answers)