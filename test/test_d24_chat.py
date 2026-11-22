from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.d23_adapter import D23AnswerAdapter
from app.chatbot.d24_metadata import MANIFEST, SOURCE


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"


class D24ChatTests(unittest.TestCase):
    def setUp(self):
        gemini = self.enterContext(patch.object(
            chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")
        ))
        self.addCleanup(gemini.assert_not_called)
        self.app = AppTest.from_file(str(CHAT_APP), default_timeout=30).run()
        self.assert_no_errors()
        self.state = self.app.session_state
        self.assertNotIn("Continue to D2.4", [button.label for button in self.app.button])
        self.state.questionnaire_complete = True
        self.app.run()
        self.click("Continue with gaps")
        self.click("Continue with gaps")

    @property
    def adapter(self):
        return self.state.d24_adapter

    def assert_no_errors(self):
        self.assertFalse(self.app.exception, [error.message for error in self.app.exception])

    def click(self, label):
        next(button for button in self.app.button if button.label == label).click().run()
        self.assert_no_errors()
        if label == "Continue with gaps":
            self.click("Confirm continue with gaps")

    def widget_key(self, record, field):
        revision = self.state.d24_revisions.get(record, 0)
        return f"d24-answer-{record}-{field}-{revision}"

    def choose_field(self, record, field):
        revision = self.state.d24_revisions.get(record, 0)
        self.app.selectbox(key=f"d24-question-{record}-{revision}").select(field).run()
        self.assert_no_errors()
        return self.widget_key(record, field)

    def draft(self, record, field, value, widget="text_area"):
        key = self.choose_field(record, field)
        getattr(self.app, widget)(key=key).set_value(value).run()
        self.assert_no_errors()
        return key

    def save(self, record, field, value, widget="text_area"):
        self.draft(record, field, value, widget)
        self.click("Confirm D2.4 answer")

    def add_record(self, kind, label):
        self.click(f"Add {label}")
        record = self.adapter.selected_record_id
        self.assertIn(record, self.adapter.record_ids(kind))
        return record

    def switch_section(self, kind):
        self.app.radio(key="d24-section").set_value(kind).run()
        self.assert_no_errors()

    def assert_scoped_draft(self, kind, first, second, field, confirmed):
        stale = self.draft(second, field, "Unconfirmed replacement")
        self.assertEqual(self.adapter.get_answers(second)[field], confirmed)
        self.assertTrue(any(item.label == "Draft answer" for item in self.app.text_area))
        self.app.button(key=f"{stale}-confirm").click()
        self.app.selectbox(key=f"d24-picker-{kind}").select(first).run()
        self.assert_no_errors()
        self.assertNotIn(f"{stale}-confirm", [button.key for button in self.app.button])
        self.assertEqual(self.adapter.get_answers(second)[field], confirmed)
        self.app.selectbox(key=f"d24-picker-{kind}").select(second).run()
        self.draft(second, field, " ")
        self.click("Confirm D2.4 answer")
        self.assertTrue(any("Expected non-empty text" in issue.value for issue in self.app.error))
        self.assertEqual(self.adapter.get_answers(second)[field], confirmed)

    def test_dataset_drafts_and_stale_confirmation_are_scoped(self):
        first = self.add_record("dataset", "dataset")
        name = "DEP-001.dataset_name_version"
        self.draft(first, name, "Dataset A")
        self.assertEqual(self.adapter.get_answers(first), {})
        self.click("Confirm D2.4 answer")
        self.save(first, "DEP-001.role", ["Training", "Other"], "multiselect")
        self.save(first, "DEP-001.role_other", "Calibration")
        self.save(first, "DEP-001.role", ["Training"], "multiselect")
        self.assertNotIn("DEP-001.role_other", self.adapter.get_answers(first))
        self.save(first, "DEP-012-trigger", "Yes", "selectbox")
        self.save(first, "DEP-012", "Two readers")
        self.save(first, "DEP-011", ["Expert read"], "multiselect")
        self.save(first, "DEP-012-trigger", "No", "selectbox")
        self.assertEqual(self.adapter.get_answers(first)["DEP-012"], "Two readers")
        self.save(first, "DEP-011", ["Pathology"], "multiselect")
        self.assertNotIn("DEP-012", self.adapter.active_fields(first))
        self.assertNotIn("DEP-012", self.adapter.get_answers(first))
        second = self.add_record("dataset", "dataset")
        stale = self.draft(second, name, "Draft B")
        self.app.button(key=f"{stale}-confirm").click()
        self.app.selectbox(key="d24-picker-dataset").select(first).run()
        self.assert_no_errors()
        self.assertEqual(self.adapter.get_answers(second), {})
        self.assertEqual(self.adapter.get_answers(first), {
            name: "Dataset A", "DEP-001.role": ["Training"], "DEP-012-trigger": "No",
            "DEP-011": ["Pathology"],
        })
        self.app.selectbox(key="d24-picker-dataset").select(second).run()
        self.save(second, name, "Dataset B")
        self.draft(second, name, " ")
        self.click("Confirm D2.4 answer")
        self.assertTrue(any("Expected non-empty text" in item.value for item in self.app.error))
        self.assertEqual(self.adapter.get_answers(second)[name], "Dataset B")
        self.assertTrue(self.app.button(key=f"d24-delete-{second}").disabled)
        self.app.checkbox(key=f"d24-remove-{second}").check().run()
        self.click("Confirm removal")
        self.assertEqual(self.adapter.record_ids("dataset"), (first,))
        self.assertEqual(self.adapter.get_answers(first)[name], "Dataset A")
        self.assertNotIn(second, self.state.d24_revisions)

    def test_evaluations_documents_and_gmlp(self):
        bridge = self.state.questionnaire_bridge
        self.assertTrue(bridge.save_answer("PIP-001", "Retained product")[0])
        self.assertTrue(bridge.save_answer("AIF-019", "No")[0])
        algorithms = D23AnswerAdapter()
        algorithm = algorithms.add_algorithm("Retained model")
        algorithms.save_answer(algorithm, "ACC-001", "Retained model v2")
        self.state.d23_adapter = algorithms
        self.state.d23_answer_revision = 0
        self.switch_section("function")
        first = self.add_record("function", "ai function / version")
        self.save(first, "DEP-019-versions", "Function v1")
        self.save(first, "DEP-028", ["Literature only"], "multiselect")
        self.assertIn("DEP-033", self.adapter.active_fields(first))
        self.assertIn("DEP-029-population", self.adapter.active_fields(first))
        self.save(first, "DEP-029-population", "Adult participants")
        self.save(first, "DEP-028", ["Reader study"], "multiselect")
        self.assertEqual(self.adapter.get_answers(first)["DEP-029-population"], "Adult participants")
        self.assertIn("DEP-030-results", self.adapter.active_fields(first))
        self.save(first, "DEP-028", ["None yet"], "multiselect")
        self.assertIn("DEP-033", self.adapter.active_fields(first))
        self.assertNotIn("DEP-029-population", self.adapter.get_answers(first))
        second = self.add_record("function", "ai function / version")
        self.save(second, "DEP-019-versions", "Function v2")
        self.assert_scoped_draft("function", first, second, "DEP-019-versions", "Function v2")
        self.app.selectbox(key="d24-picker-function").select(first).run()
        self.assertEqual(self.adapter.selected_record_id, first)
        self.assertEqual(self.adapter.get_answers(second), {"DEP-019-versions": "Function v2"})
        self.switch_section("document")
        doc = self.add_record("document", "supporting document")
        self.save(doc, "title", "Evaluation report")
        for field, value in {
            "document_id": "Report-1", "version": "v2", "date": "2026-11-01",
            "supported_fields": "DEP-028", "page_section": "Section 5",
        }.items():
            self.save(doc, field, value)
        self.assertEqual(self.adapter.get_answers(doc)["page_section"], "Section 5")
        second_doc = self.add_record("document", "supporting document")
        self.save(second_doc, "title", "Protocol")
        self.save(second_doc, "document_id", "Protocol-2")
        self.assert_scoped_draft("document", doc, second_doc, "document_id", "Protocol-2")
        self.assertEqual(self.adapter.record_ids("function"), (first, second))
        self.switch_section("gmlp")
        gmlp = self.adapter.GMLP
        self.assertNotIn("DEP-036", self.adapter.active_fields(gmlp))
        self.draft(gmlp, "DEP-036-trigger", "Yes", "selectbox")
        self.assertEqual(self.adapter.get_answers(gmlp), {})
        self.click("Confirm D2.4 answer")
        self.save(gmlp, "DEP-036", "Partly", "selectbox")
        self.save(gmlp, "DEP-036-document", "Report-2")
        self.assertEqual(self.adapter.get_answers(gmlp)["DEP-036-document"], "Report-2")
        datasets = []
        self.switch_section("dataset")
        for name in ("Training set", "Evaluation set"):
            dataset = self.add_record("dataset", "dataset")
            self.save(dataset, "DEP-001.dataset_name_version", name)
            datasets.append(dataset)
        records = (*datasets, first, second, doc, second_doc, gmlp)
        snapshot = {record: self.adapter.get_answers(record) for record in records}
        self.click("Back to D2.3")
        self.assertEqual(algorithms.get_algorithm(algorithm)["answers"]["ACC-001"]["value"], "Retained model v2")
        self.click("Back to D2.1 and D2.2")
        self.assertEqual(bridge.get_product_profile(), {"PIP-001": "Retained product", "AIF-019": "No"})
        self.click("Continue with gaps")
        self.click("Continue with gaps")
        self.assertEqual({record: self.adapter.get_answers(record) for record in records}, snapshot)
        for kind, remove, keep in (("function", second, first), ("document", second_doc, doc)):
            self.switch_section(kind)
            self.app.selectbox(key=f"d24-picker-{kind}").select(remove).run()
            self.assertTrue(self.app.button(key=f"d24-delete-{remove}").disabled)
            self.app.checkbox(key=f"d24-remove-{remove}").check().run()
            self.click("Confirm removal")
            self.assertEqual(self.adapter.record_ids(kind), (keep,))
            self.assertEqual(self.adapter.get_answers(keep), snapshot[keep])
            self.assertEqual(self.adapter.record_ids("dataset"), tuple(datasets))
        self.switch_section("gmlp")
        self.save(gmlp, "DEP-036-trigger", "No", "selectbox")
        self.assertEqual(self.adapter.get_answers(gmlp), {"DEP-036-trigger": "No"})
        self.assertFalse(any(button.key == "d24-add-gmlp" for button in self.app.button))

    def test_navigation_preserves_previous_sections_and_confirmed_records(self):
        bridge = self.state.questionnaire_bridge
        self.assertTrue(bridge.save_answer("PIP-001", "Existing product")[0])
        self.assertTrue(bridge.save_answer("AIF-019", "No")[0])
        algorithms = D23AnswerAdapter()
        algorithm = algorithms.add_algorithm("Existing model")
        algorithms.save_answer(algorithm, "ACC-001", "Existing model v1")
        self.state.d23_adapter = algorithms
        self.state.d23_answer_revision = 0
        dataset = self.add_record("dataset", "dataset")
        self.save(dataset, "DEP-001.dataset_name_version", "Persistent dataset")
        d24 = self.adapter
        self.app.run()
        self.click("Back to D2.3")
        self.assertIs(self.state.d23_adapter, algorithms)
        self.assertEqual(algorithms.get_algorithm(algorithm)["answers"]["ACC-001"]["value"], "Existing model v1")
        self.click("Back to D2.1 and D2.2")
        self.assertIs(self.state.questionnaire_bridge, bridge)
        self.assertEqual(bridge.get_product_profile(), {"PIP-001": "Existing product", "AIF-019": "No"})
        self.click("Continue with gaps")
        self.click("Continue with gaps")
        self.assertIs(self.adapter, d24)
        self.assertEqual(d24.get_answers(dataset), {"DEP-001.dataset_name_version": "Persistent dataset"})

    def test_compatibility_failure_disables_edits_without_losing_confirmed_answers(self):
        dataset = self.add_record("dataset", "dataset")
        self.save(dataset, "DEP-001.dataset_name_version", "Confirmed name")
        stale = self.draft(dataset, "DEP-001.source_documentation", "Unconfirmed reference")
        directory = Path(self.enterContext(TemporaryDirectory()))
        owner = directory / SOURCE.name
        owner.write_bytes(SOURCE.read_bytes() + b"\n# unreviewed change\n")
        manifest = MANIFEST.read_bytes()
        with patch("app.chatbot.d24_metadata.SOURCE", owner):
            self.app.button(key=f"{stale}-confirm").click().run()
            self.assert_no_errors()
            self.assertTrue(any("compatibility manifest requires review" in item.value for item in self.app.error))
            self.assertNotIn("Confirm D2.4 answer", [button.label for button in self.app.button])
            self.assertNotIn("Add dataset", [button.label for button in self.app.button])
            self.assertEqual(self.adapter.get_answers(dataset), {"DEP-001.dataset_name_version": "Confirmed name"})
            self.click("Back to D2.3")
            self.assertIn("Add algorithm", [button.label for button in self.app.button])
            self.click("Back to D2.1 and D2.2")
            self.assertTrue(self.app.chat_input)
            self.click("Continue with gaps")
            self.click("Continue with gaps")
            self.assertTrue(self.app.error)
        self.assertEqual(MANIFEST.read_bytes(), manifest)
        self.app.run()
        self.assert_no_errors()
        self.assertIn("Confirm D2.4 answer", [button.label for button in self.app.button])
