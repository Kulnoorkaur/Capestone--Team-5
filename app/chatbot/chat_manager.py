"""
AI Regulatory Readiness Platform
Context-Aware Chat Manager

Manages:
- Questionnaire progression
- Confirmed user answers
- Previous answers for Gemini context
- Suggested answers based on earlier information
- User confirmation of suggested answers
"""

from copy import deepcopy


PRODUCT_QUESTIONS = [
    {
        "id": "product_name",
        "question": "What is your product's name?",
    },
    {
        "id": "product_description",
        "question": "What does your medical AI product do?",
    },
    {
        "id": "intended_use",
        "question": (
            "What is the intended medical purpose of your product? "
            "For example, does it help detect, diagnose, monitor, "
            "or predict a medical condition?"
        ),
    },
    {
        "id": "target_users",
        "question": (
            "Who are the intended users of your product? "
            "For example, radiologists, physicians, "
            "technicians, or patients?"
        ),
    },
    {
        "id": "patient_population",
        "question": (
            "What patient population is your product "
            "intended to be used for?"
        ),
    },
    {
        "id": "clinical_setting",
        "question": (
            "In what clinical setting will your product "
            "be used? For example, hospitals, imaging "
            "centres, or outpatient clinics?"
        ),
    },
    {
        "id": "ai_function",
        "question": (
            "What specific task does the AI perform? "
            "For example, detection, classification, "
            "segmentation, prediction, or measurement?"
        ),
    },
    {
        "id": "human_oversight",
        "question": (
            "How are healthcare professionals involved "
            "in reviewing or acting on the AI's output?"
        ),
    },
    {
        "id": "jurisdiction",
        "question": (
            "In which regulatory jurisdiction do you "
            "intend to market your product? "
            "For example, Canada or the United States?"
        ),
    },
]


class ChatManager:
    """
    Controls the structured product questionnaire.

    Only explicitly accepted answers are saved as confirmed.

    AI-generated suggestions are stored separately until
    the user confirms or corrects them.
    """

    def __init__(self):
        self.questions = deepcopy(PRODUCT_QUESTIONS)
        self.current_index = 0
        self.answers = {}
        self.suggestions = {}

    def get_current_question(self):
        """Return the current question or None if complete."""

        if self.current_index >= len(self.questions):
            return None

        return deepcopy(self.questions[self.current_index])

    def save_answer(self, answer):
        """
        Save an explicitly provided answer and advance.

        Returns True if saved successfully.
        """

        if self.is_complete():
            return False

        if not isinstance(answer, str) or not answer.strip():
            return False

        question = self.get_current_question()

        self.answers[question["id"]] = answer.strip()

        # Remove any pending suggestion for this field.
        self.suggestions.pop(question["id"], None)

        self.current_index += 1

        return True

    def suggest_answer(self, question_id, suggested_answer):
        """
        Store a proposed answer without confirming it.

        Suggestions must not be treated as user-confirmed facts.
        """

        valid_ids = {
            question["id"] for question in self.questions
        }

        if question_id not in valid_ids:
            return False

        if (
            not isinstance(suggested_answer, str)
            or not suggested_answer.strip()
        ):
            return False

        self.suggestions[question_id] = suggested_answer.strip()

        return True

    def get_suggestion(self, question_id=None):
        """
        Retrieve a proposed answer.

        Defaults to the current questionnaire field.
        """

        if question_id is None:
            question = self.get_current_question()

            if question is None:
                return None

            question_id = question["id"]

        return self.suggestions.get(question_id)

    def confirm_suggestion(self):
        """
        Save the current suggestion only after the user
        explicitly confirms it.

        Returns True if confirmation succeeded.
        """

        question = self.get_current_question()

        if question is None:
            return False

        suggested_answer = self.get_suggestion(question["id"])

        if not suggested_answer:
            return False

        return self.save_answer(suggested_answer)

    def reject_suggestion(self):
        """
        Remove the current suggestion without saving it.
        """

        question = self.get_current_question()

        if question is None:
            return False

        return self.suggestions.pop(
            question["id"], None
        ) is not None

    def get_previous_answers(self):
        """
        Return confirmed answers as context for Gemini.

        Excludes unconfirmed suggestions.
        """

        return deepcopy(self.answers)

    def get_answers(self):
        """Return a copy of all confirmed answers."""

        return deepcopy(self.answers)

    def get_progress(self):
        """Return questionnaire completion percentage."""

        if not self.questions:
            return 100

        return round(
            (self.current_index / len(self.questions)) * 100
        )

    def is_complete(self):
        """Check whether all questions are completed."""

        return self.current_index >= len(self.questions)

    def previous_question(self):
        """
        Move back one question without deleting its answer.
        """

        if self.current_index <= 0:
            return None

        self.current_index -= 1

        return self.get_current_question()

    def get_product_profile(self):
        """
        Return the structured product profile.

        Each field includes its confirmed answer, if available.
        """

        profile = {}

        for question in self.questions:
            question_id = question["id"]

            profile[question_id] = {
                "question": question["question"],
                "answer": self.answers.get(question_id),
                "confirmed": question_id in self.answers,
            }

        return profile

    def reset(self):
        """Start a new questionnaire session."""

        self.current_index = 0
        self.answers = {}
        self.suggestions = {}