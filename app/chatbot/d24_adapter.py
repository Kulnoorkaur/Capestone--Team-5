"""Confirmed D2.4 answers and a compatibility layer for the owner renderer."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from app.chatbot.d24_metadata import check_metadata_compatibility, load_metadata
from app.deliverable_3.dataset_validation import validate_dataset_evidence


RecordKind = Literal["dataset", "function", "document"]
_RECORD_LABELS = {
    "dataset": "Dataset 1",
    "function": "AI Function / Version 1",
    "document": "Supporting Document 1",
}


@dataclass
class _Record:
    kind: str
    answers: dict


class D24AnswerAdapter:
    """Store only confirmed answers, keyed by stable IDs independent of names."""

    GMLP = "gmlp"

    def __init__(self):
        self._metadata = load_metadata()
        self._records = {}
        self._next_id = 1
        self._gmlp = _Record("gmlp", {})
        self._selected_record_id = None

    @property
    def selected_record_id(self):
        return self._selected_record_id

    def record_ids(self, kind: RecordKind):
        return tuple(record_id for record_id, record in self._records.items() if record.kind == kind)

    def create_record(self, kind: RecordKind):
        if kind not in self._metadata.sections:
            raise ValueError(f"Unknown record kind: {kind}.")
        record_id = f"{kind}-{self._next_id}"
        self._next_id += 1
        self._records[record_id] = _Record(kind, {})
        return record_id

    def select_record(self, record_id):
        self._record(record_id)
        self._selected_record_id = record_id

    def remove_record(self, record_id):
        del self._records[record_id]
        if self._selected_record_id == record_id:
            self._selected_record_id = None

    def get_answers(self, record_id):
        return deepcopy(self._record(record_id).answers)

    def check_compatibility(self):
        check_metadata_compatibility(self._metadata.fingerprint)

    def field_ids(self, record_id):
        """Return all known fields for the record, including inactive fields."""
        return self._metadata.field_ids(self._record(record_id).kind)

    def active_fields(self, record_id):
        """Return the owner-visible field descriptions, including unanswered fields."""
        record = self._record(record_id)
        return self._metadata.project(record.kind, record.answers)[1]

    def save_answer(self, record_id, field_id, value):
        record = self._record(record_id)
        field = self.active_fields(record_id).get(field_id)
        if field is None:
            raise ValueError(f"{field_id}: Unknown or inactive field for this record.")
        try:
            field.check(value)
        except ValueError as error:
            raise ValueError(f"{field_id}: {error}") from error
        candidate = {**record.answers, field_id: deepcopy(value)}
        _, active = self._metadata.project(record.kind, candidate)
        record.answers = {key: answer for key, answer in candidate.items() if key in active}

    def native_profile(self):
        """Match renderer defaults and conditional nulls without confirming them."""
        profile = {section: [] for section in self._metadata.sections.values()}
        for record in self._records.values():
            profile[self._metadata.sections[record.kind]].append(self._native_record(record))
        profile.update(self._native_record(self._gmlp))
        return profile

    def validate(self):
        return validate_dataset_evidence(self.native_profile())

    def validate_record(self, record_id):
        record = self._record(record_id)
        if record.kind == "gmlp":
            profile = self._native_record(record)
            label = "GMLP"
        else:
            section = self._metadata.sections[record.kind]
            profile = {section: [self._native_record(record)]}
            label = _RECORD_LABELS[record.kind]
        return [issue for issue in validate_dataset_evidence(profile) if issue["record"] == label]

    def _record(self, record_id):
        return self._gmlp if record_id == self.GMLP else self._records[record_id]

    def _native_record(self, record):
        return self._metadata.project(record.kind, record.answers)[0]
