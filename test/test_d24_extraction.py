import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.d24_adapter import D24AnswerAdapter

CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"

def proposal(value, quote, **extra):
    return {"value": value, "quote": quote, **extra}


class D24EvidenceTests(unittest.TestCase):
    def extract(self, message, candidates, *, scope="function", previous=(), other_labels=(), target=None, calls=1):
        adapter = D24AnswerAdapter()
        record_id = adapter.GMLP if scope == "gmlp" else adapter.create_record(scope)
        response = {"record_id": record_id, "scope": scope, "source_id": "1", "candidates": candidates}
        with patch.object(chat_llm, "_request_extraction", return_value=response) as request:
            result = chat_llm.extract_d24_candidates(
                message, record_id=record_id, scope=scope, record_label=record_id,
                source_id="1", fields=adapter.field_variants(record_id),
                active_fields=adapter.active_fields(record_id), target_field=target,
                confirmed={}, other_labels=other_labels, previous=previous,
            )
        self.assertEqual(request.call_count, calls)
        return result

    def test_rejects_invalid_values_fabricated_evidence_and_unquoted_metrics(self):
        message = "The dataset was Mixed. Sample size: 100 patients."
        accepted, _ = self.extract(message, {
            "DEP-003": proposal("Mixed", "The dataset was Mixed."),
            "DEP-005": proposal("500 patients", "100 patients"),
            "DEP-001.role": proposal("Training", "The dataset was Mixed."),
            "DEP-001.source_documentation": proposal("Report-9", "Report-9"),
            "DEP-004": proposal(["Approved"], "The dataset was Mixed."),
            "DEP-999": proposal("Mixed", "Mixed"),
        }, scope="dataset")
        self.assertEqual(list(accepted), ["DEP-003"])
        accepted, _ = self.extract("Sensitivity was measured.", {
            "DEP-020-metrics": proposal(["Sensitivity", "Specificity"], "Sensitivity was measured."),
            "DEP-021-report": proposal("Report-4", "Sensitivity was measured.", explanation="Report-4"),
        })
        self.assertEqual(accepted, {})
        accepted, _ = self.extract("We completed a Reader study.", {
            "DEP-028": proposal(["Reader study"], "We completed a Reader study."),
        })
        self.assertIn("DEP-028", accepted)

    def test_excerpt_cannot_omit_planning_negation_or_contradiction(self):
        for message, candidate, previous in (
            ("A Reader study is planned.", {"DEP-028": proposal(["Reader study"], "Reader study")}, ()),
            ("We did not use IEC 62304.", {"DEP-026-standard": proposal("IEC 62304", "IEC 62304.")}, ()),
            ("Sensitivity was 88%. Sensitivity was 92%.", {"DEP-030-results": proposal("92%", "92%.")}, ()),
            ("Sensitivity was 92%.", {"DEP-030-results": proposal("92%", "92%")}, ("Sensitivity was 88%.",)),
        ):
            with self.subTest(message=message, previous=previous):
                self.assertEqual(self.extract(message, candidate, previous=previous)[0], {})
        accepted, _ = self.extract("Yes, a human study is planned.", {
            "DEP-034": proposal("Yes", "Yes, a human study is planned."),
        }, target="DEP-034")
        self.assertIn("DEP-034", accepted)

    def test_ambiguous_attribution_requests_clarification_before_calling(self):
        accepted, clarification = self.extract(
            "Primary collection is Mixed, but Holdout collection is Prospective.",
            {"DEP-003": proposal("Mixed", "Mixed")}, scope="dataset", other_labels=("Holdout collection",), calls=0,
        )
        self.assertEqual(accepted, {})
        self.assertIn("selected record", clarification)

    def test_measurement_disambiguation_cases(self):
        cases = (
            ("A", "The dataset contains 500 scans. Actually, it contains 700 scans.",
             "DEP-005", "700 scans", "dataset", True),
            ("B", "Dataset A contains 500 scans. Dataset B contains 700 scans.",
             "DEP-005", "700 scans", "dataset", False),
            ("C", "The training set contains 500 scans and the test set contains 700 scans.",
             "DEP-005", "700 scans", "dataset", False),
            ("D", "The dataset contains 500 patients and 700 scans.",
             "DEP-005", "700 scans", "dataset", False),
            ("E", "The dataset initially contained 500 scans and later expanded to 700 scans.",
             "DEP-005", "700 scans", "dataset", False),
            ("F", "The model sensitivity was 85%. Actually, it was 92%.",
             "DEP-030-results", "92%", "function", True),
            ("G", "The dataset contains 500 scans. Correction: it contains 700 scans.",
             "DEP-005", "700 scans", "dataset", True),
            ("H", "The dataset contains 500 scans collected retrospectively.",
             "DEP-005", "500 scans", "dataset", False),
        )
        for case, message, field, value, kind, conflict in cases:
            with self.subTest(case=case):
                self.assertEqual(bool(chat_llm._d24_measurement_conflicts((message,))), conflict)
                accepted, clarification = self.extract(
                    message, {field: proposal(value, value)}, scope=kind, calls=0 if case == "B" else 1,
                )
                if conflict or case == "B":
                    self.assertEqual(accepted, {})
                    self.assertIn("Which value is correct" if conflict else "selected record", clarification)
                else:
                    self.assertEqual(accepted[field]["value"], value)
                    self.assertEqual(clarification, "")

    def test_conflicting_counts_leave_independent_suggestions_available(self):
        message = "The dataset contains 500 scans. Actually, it contains 700 scans. Collection was Retrospective."
        accepted, clarification = self.extract(message, {
            "DEP-005": proposal("700 scans", "700 scans"),
            "DEP-003": proposal("Retrospective", "Collection was Retrospective."),
        }, scope="dataset")
        self.assertEqual(set(accepted), {"DEP-003"})
        self.assertIn("Which value is correct", clarification)

    def test_unattributed_counts_prompt_for_clarification(self):
        accepted, clarification = self.extract(
            "500 scans. 700 scans.", {"DEP-005": proposal("700 scans", "700 scans")}, scope="dataset",
        )
        self.assertEqual(accepted, {})
        self.assertIn("Which value is correct", clarification)

    def test_wrong_record_echo_rejects_the_whole_response(self):
        adapter = D24AnswerAdapter()
        record = adapter.create_record("dataset")
        with patch.object(chat_llm, "_request_extraction", return_value={
            "record_id": "dataset-99", "scope": "dataset", "source_id": "1",
            "candidates": {"DEP-003": proposal("Mixed", "Mixed")},
        }), self.assertRaisesRegex(ValueError, "mismatched record"):
            chat_llm.extract_d24_candidates(
                "Mixed", record_id=record, scope="dataset", record_label=record,
                source_id="1", fields=adapter.field_variants(record),
                active_fields=adapter.active_fields(record), target_field="DEP-003", confirmed={},
            )
        self.assertEqual(adapter.get_answers(record), {})


class D24ExtractionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.response = {}
        self.requests = []
        self.failure = None

        def generate(**kwargs):
            payload = json.loads("{" + kwargs["contents"].split("\n{", 1)[1])
            self.requests.append(payload)
            if self.failure:
                if isinstance(self.failure, Exception):
                    raise self.failure
                return SimpleNamespace(text=self.failure)
            response = {key: payload[key] for key in ("record_id", "scope", "source_id")}
            return SimpleNamespace(text=json.dumps({**response, "candidates": self.response}))

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        self.enterContext(patch.object(chat_llm, "get_gemini_client", return_value=client))
        self.app = AppTest.from_file(str(CHAT_APP), default_timeout=30).run()
        self.state = self.app.session_state
        self.state.questionnaire_complete = True
        self.app.run()
        self.click("Continue to D2.3")
        self.click("Continue to D2.4")

    @property
    def adapter(self):
        return self.state.d24_adapter

    def click(self, label):
        next(button for button in self.app.button if button.label == label).click().run()
        self.assertFalse(self.app.exception)

    def add(self, label):
        self.click(label)
        return self.adapter.selected_record_id

    def scope(self, scope):
        self.app.radio(key="d24-section").set_value(scope).run()
        self.assertFalse(self.app.exception)

    def submit(self, record_id, message, candidates):
        self.response = candidates
        self.app.chat_input(key=f"d24-message-{record_id}").set_value(message).run()
        self.assertFalse(self.app.exception)

    def review_button(self, field, action="confirm"):
        return next(button for button in self.app.button
                    if (button.key or "").startswith("d24-review-") and f"-{field}-" in button.key
                    and button.key.endswith(f"-{action}"))

    def test_dataset_multi_field_confirm_edit_reject_and_conditional_staging(self):
        record = self.add("Add dataset")
        message = "The role is Other: calibration. Collection was Mixed."
        self.submit(record, message, {
            "DEP-001.role_other": proposal("calibration", "Other: calibration"),
            "DEP-001.role": proposal(["Other"], "The role is Other: calibration", explanation="The user named the role."),
            "DEP-003": proposal("Mixed", "Collection was Mixed."),
        })
        self.assertEqual(self.adapter.get_answers(record), {})
        self.assertFalse(any("role_other" in (button.key or "") for button in self.app.button))
        self.review_button("DEP-001.role").click().run()
        self.assertEqual(self.adapter.get_answers(record), {"DEP-001.role": ["Other"]})
        button = self.review_button("DEP-001.role_other")
        self.app.text_area(key=button.key.removesuffix("-confirm")).set_value("Calibration dataset")
        button.click().run()
        self.review_button("DEP-003", "reject").click().run()
        self.assertEqual(self.adapter.get_answers(record), {
            "DEP-001.role": ["Other"], "DEP-001.role_other": "Calibration dataset",
        })
        self.assertEqual(len(self.requests), 1)

    def test_editing_parent_discards_dependent_and_stale_click_cannot_cross_record(self):
        first = self.add("Add dataset")
        self.submit(first, "Other: calibration.", {
            "DEP-001.role": proposal(["Other"], "Other: calibration."),
            "DEP-001.role_other": proposal("calibration", "Other: calibration."),
        })
        button = self.review_button("DEP-001.role")
        self.app.multiselect(key=button.key.removesuffix("-confirm")).set_value(["Training"])
        button.click().run()
        self.assertEqual(self.state.d24_conversations[first]["pending"], {})
        self.submit(first, "Mixed.", {"DEP-003": proposal("Mixed", "Mixed.")})
        stale = self.review_button("DEP-003")
        stale.click()
        second = self.add("Add dataset")
        self.assertEqual(self.adapter.get_answers(first), {"DEP-001.role": ["Training"]})
        self.assertEqual(self.adapter.get_answers(second), {})
        self.assertNotIn(stale.key, [button.key for button in self.app.button])
        self.app.selectbox(key="d24-picker-dataset").select(first).run()
        self.app.checkbox(key=f"d24-remove-{first}").check().run()
        self.click("Confirm removal")
        self.assertNotIn(first, self.state.d24_conversations)
        self.assertEqual(self.adapter.record_ids("dataset"), (second,))
        self.assertEqual(len(self.requests), 2)

    def test_evaluation_document_and_gmlp_scopes(self):
        for scope, button, field, value, message in (
            ("function", "Add ai function / version", "DEP-020-metrics", ["Sensitivity"], "Metric: Sensitivity."),
            ("document", "Add supporting document", "document_id", "Study-17", "Document identifier Study-17."),
            ("gmlp", None, "DEP-036-trigger", "Yes", "Yes"),
        ):
            self.scope(scope)
            record = self.add(button) if button else self.adapter.GMLP
            self.submit(record, message, {field: proposal(value, message)})
            self.assertEqual(self.requests[-1]["scope"], scope)
            self.assertEqual(self.requests[-1]["record_id"], record)
            self.assertEqual(self.adapter.get_answers(record), {})
            self.review_button(field).click().run()
            self.assertEqual(self.adapter.get_answers(record), {field: value})
        self.assertEqual(len(self.requests), 3)

    def test_malformed_and_failed_calls_keep_record_and_manual_fallback(self):
        record = self.add("Add dataset")
        self.app.text_area(key=f"d24-answer-{record}-DEP-001.dataset_name_version-0").set_value("Confirmed dataset")
        self.click("Confirm D2.4 answer")
        for failure in (TimeoutError("timeout"), "{not valid"):
            self.failure = failure
            self.submit(record, "A new message.", {})
            self.assertTrue(any("could not process" in item.value for item in self.app.info))
            self.assertEqual(self.adapter.selected_record_id, record)
            self.assertEqual(self.adapter.get_answers(record), {"DEP-001.dataset_name_version": "Confirmed dataset"})
            self.assertTrue(any(button.label == "Confirm D2.4 answer" for button in self.app.button))
        self.assertEqual(len(self.requests), 2)

    def test_later_conflicting_turn_clears_unconfirmed_suggestion(self):
        record = self.add("Add dataset")
        self.submit(record, "The dataset contains 100 patients.", {
            "DEP-005": proposal("100 patients", "100 patients"),
        })
        self.review_button("DEP-005")
        self.submit(record, "The dataset contains 200 patients.", {
            "DEP-005": proposal("200 patients", "200 patients"),
        })
        self.assertEqual(self.state.d24_conversations[record]["pending"], {})
        self.assertEqual(self.adapter.get_answers(record), {})
        self.assertEqual(len(self.requests), 2)

    def test_conflicting_turn_keeps_confirmed_answers_and_independent_review(self):
        record = self.add("Add dataset")
        self.app.text_area(key=f"d24-answer-{record}-DEP-001.dataset_name_version-0").set_value("Existing dataset")
        self.click("Confirm D2.4 answer")
        message = "The dataset contains 500 scans. Actually, it contains 700 scans. Collection was Retrospective."
        self.submit(record, message, {
            "DEP-005": proposal("700 scans", "700 scans"),
            "DEP-003": proposal("Retrospective", "Collection was Retrospective."),
        })
        self.assertTrue(any("Which value is correct" in item.value for item in self.app.info))
        self.assertFalse(any("-DEP-005-" in (button.key or "") for button in self.app.button))
        self.assertEqual(self.adapter.get_answers(record), {"DEP-001.dataset_name_version": "Existing dataset"})
        self.review_button("DEP-003").click().run()
        self.assertEqual(self.adapter.get_answers(record), {
            "DEP-001.dataset_name_version": "Existing dataset", "DEP-003": "Retrospective",
        })
        self.assertEqual(len(self.requests), 1)
