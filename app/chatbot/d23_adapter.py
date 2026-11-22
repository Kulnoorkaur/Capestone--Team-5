"""In-memory, algorithm-scoped confirmed answers for Chat Buddy's D2.3."""

from copy import deepcopy
from dataclasses import dataclass, field

from app.deliverable_2.questionnaires.algorithm_change_control import (
    FIELDS,
    FRAMEWORKS,
    build_record,
    is_active,
    needs_details,
    validate,
)


AnswerValue = str | list[str] | dict[str, str | None]
FIELDS_BY_ID = {definition["id"]: definition for definition in FIELDS}


@dataclass
class _Algorithm:
    name: str
    version: str
    answers: dict = field(default_factory=dict)
    source_quotes: dict = field(default_factory=dict)


class D23AnswerAdapter:
    """Store confirmed answers only. Callers manage suggestion review."""

    def __init__(self):
        self._algorithms: dict[str, _Algorithm] = {}
        self._next_algorithm_number = 1

    @property
    def algorithm_ids(self) -> tuple[str, ...]:
        return tuple(self._algorithms)

    def add_algorithm(self, name: str, version: str = "", *, algorithm_id: str | None = None) -> str:
        """Create a named record without confirming any questionnaire fields."""
        self._validate_identity(name, version)
        if algorithm_id is None:
            while True:
                algorithm_id = f"algorithm-{self._next_algorithm_number}"
                self._next_algorithm_number += 1
                if algorithm_id not in self._algorithms:
                    break
        elif not isinstance(algorithm_id, str) or not algorithm_id.strip():
            raise ValueError("Algorithm ID must be non-empty text.")
        elif algorithm_id in self._algorithms:
            raise ValueError(f"Duplicate algorithm ID: {algorithm_id}.")
        self._algorithms[algorithm_id] = _Algorithm(name, version)
        return algorithm_id

    def update_identity(self, algorithm_id: str, name: str, version: str) -> None:
        """Update display metadata while keeping the same ID and answers."""
        algorithm = self._algorithms[algorithm_id]
        self._validate_identity(name, version)
        algorithm.name = name
        algorithm.version = version

    def get_algorithm(self, algorithm_id: str) -> dict:
        """Return a detached snapshot, including chat-only source quotes."""
        algorithm = self._algorithms[algorithm_id]
        return deepcopy({
            "name": algorithm.name,
            "version": algorithm.version,
            "answers": algorithm.answers,
            "source_quotes": algorithm.source_quotes,
        })

    def active_field_ids(self, algorithm_id: str) -> tuple[str, ...]:
        answers = self._algorithms[algorithm_id].answers
        return tuple(field_id for field_id in FIELDS_BY_ID if is_active(field_id, answers))

    def save_answer(
        self, algorithm_id: str, field_id: str, value: AnswerValue, *,
        details: str = "", evidence: str = "", source_quote: str = "",
    ) -> None:
        """Replace a confirmed answer atomically. Omitted metadata is cleared.

        Missing explanations and document references remain review findings.
        A partial framework map is allowed and remains an incomplete answer.
        """
        algorithm = self._algorithms[algorithm_id]
        answers = self._checked_answers(algorithm, field_id, value, details, evidence)
        if not isinstance(source_quote, str):
            raise ValueError(f"{field_id}: source quote must be text.")
        quotes = {key: quote for key, quote in algorithm.source_quotes.items() if key != field_id}
        if source_quote:
            quotes[field_id] = source_quote
        self._store_active_answers(algorithm, answers, quotes)

    def check_answer(self, algorithm_id: str, field_id: str, value: AnswerValue, *, details: str = "") -> None:
        """Check a candidate against current activation and owner validation."""
        self._checked_answers(self._algorithms[algorithm_id], field_id, value, details, "")

    def _checked_answers(self, algorithm, field_id, value, details, evidence):
        definition = FIELDS_BY_ID.get(field_id)
        if definition is None:
            raise ValueError(f"Unknown D2.3 field: {field_id}.")
        if not is_active(field_id, algorithm.answers):
            raise ValueError(f"{field_id}: This conditional question is inactive.")
        for label, text in (("details", details), ("evidence", evidence)):
            if not isinstance(text, str):
                raise ValueError(f"{field_id}: {label} must be text.")
        self._validate_value(definition, value)

        answers = {
            **algorithm.answers,
            field_id: {"value": deepcopy(value), "details": details, "evidence": evidence},
        }
        # The owner validator returns errors and completeness gaps in the same
        # list. Permit only the two gaps that can apply to a saved partial answer.
        for issue in validate(answers):
            if issue["id"] != field_id:
                continue
            problem = issue["problem"]
            if definition["type"] == "perframework" and problem == "Required answer missing":
                continue
            if needs_details(field_id, value) and problem.startswith("Explanation required"):
                continue
            raise ValueError(f"{field_id}: {problem}.")

        return answers

    def remove_answer(self, algorithm_id: str, field_id: str) -> None:
        """Clear a confirmed answer and any descendants it deactivates."""
        algorithm = self._algorithms[algorithm_id]
        if field_id not in FIELDS_BY_ID:
            raise ValueError(f"Unknown D2.3 field: {field_id}.")
        answers = {key: answer for key, answer in algorithm.answers.items() if key != field_id}
        self._store_active_answers(algorithm, answers, algorithm.source_quotes)

    def build_record(self, algorithm_id: str) -> dict:
        """Return the native D2.3 record with owner validation and evaluation."""
        algorithm = self._algorithms[algorithm_id]
        record_name = f"{algorithm.name} — {algorithm.version}" if algorithm.version else algorithm.name
        return build_record(record_name, deepcopy(algorithm.answers))

    @staticmethod
    def _validate_identity(name: str, version: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("An algorithm name is required.")
        if not isinstance(version, str):
            raise ValueError("Algorithm version must be text.")

    @staticmethod
    def _validate_value(definition: dict, value: AnswerValue) -> None:
        field_id = definition["id"]
        field_type = definition["type"]
        options = definition["options"]
        if field_type in ("text", "longtext"):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_id}: Expected non-empty text.")
        elif field_type == "select":
            if not isinstance(value, str) or value not in options:
                raise ValueError(f"{field_id}: Expected an allowed option.")
        elif field_type == "multiselect":
            if not isinstance(value, list) or not value or any(item not in options for item in value):
                raise ValueError(f"{field_id}: Expected a non-empty list of allowed options.")
        elif field_type == "perframework":
            if not isinstance(value, dict):
                raise ValueError(f"{field_id}: Expected a dictionary of framework statuses.")
            for framework, status in value.items():
                if framework not in FRAMEWORKS:
                    raise ValueError(f"{field_id}: Unknown framework {framework!r}.")
                if status is not None and status not in options:
                    raise ValueError(f"{field_id}: Invalid status for {framework}.")
        else:
            raise ValueError(f"{field_id}: Unsupported D2.3 field type {field_type!r}.")

    @staticmethod
    def _store_active_answers(algorithm: _Algorithm, answers: dict, quotes: dict) -> None:
        algorithm.answers = {
            field_id: answer for field_id, answer in answers.items() if is_active(field_id, answers)
        }
        algorithm.source_quotes = {
            field_id: quote for field_id, quote in quotes.items() if field_id in algorithm.answers
        }
