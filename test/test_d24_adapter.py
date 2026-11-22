from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.d24_adapter import D24AnswerAdapter
from app.chatbot.d24_metadata import D24CompatibilityError, MANIFEST, SOURCE, load_metadata
from app.deliverable_3.dataset_validation import validate_dataset_evidence


class D24AdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = D24AnswerAdapter()
        gemini = self.enterContext(patch.object(
            chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")
        ))
        self.addCleanup(gemini.assert_not_called)

    def test_empty_profile(self):
        native = self.adapter.native_profile()
        self.assertEqual(native, {
            "datasets": [], "ai_function_versions": [], "evidence_documents": [],
            "DEP-036-trigger": "Select an option", "DEP-036": None, "DEP-036-document": None,
        })
        self.assertEqual(self.adapter.get_answers(self.adapter.GMLP), {})
        self.assertEqual(self.adapter.validate(), validate_dataset_evidence(native))
        self.assertEqual({issue["field_id"] for issue in self.adapter.validate()},
                         {"DEP-001", "DEP-019", "DEP-035"})

    def test_repeatable_records_keep_stable_identity_and_isolated_answers(self):
        a = self.adapter
        for kind, key, identifier, detail in (
            ("dataset", "datasets", "DEP-001.dataset_name_version", "DEP-002"),
            ("function", "ai_function_versions", "DEP-019-versions", "DEP-020-criteria"),
            ("document", "evidence_documents", "title", "document_id"),
        ):
            with self.subTest(kind=kind):
                first, second = a.create_record(kind), a.create_record(kind)
                for record_id, value in ((first, "First reference"), (second, "Second reference")):
                    a.select_record(record_id)
                    a.save_answer(record_id, identifier, "Shared display name")
                    a.save_answer(record_id, detail, value)
                self.assertEqual(a.selected_record_id, second)
                self.assertEqual(a.record_ids(kind), (first, second))
                a.save_answer(first, identifier, "Renamed")
                rows = a.native_profile()[key]
                self.assertEqual([row[detail] for row in rows], ["First reference", "Second reference"])
                self.assertNotIn(first, repr(rows))
                self.assertNotIn(second, repr(rows))
                a.remove_record(second)
                self.assertIsNone(a.selected_record_id)
                self.assertEqual(a.record_ids(kind), (first,))
                self.assertNotIn(a.create_record(kind), (first, second))

    def test_nested_inventory_types_and_atomic_rejection(self):
        a = self.adapter
        dataset = a.create_record("dataset")
        a.save_answer(dataset, "DEP-001.dataset_name_version", "Dataset v1")
        a.save_answer(dataset, "DEP-001.role", ["Other", "Training"])
        a.save_answer(dataset, "DEP-001.role_other", "Calibration")
        a.save_answer(dataset, "DEP-001.source_documentation", "Protocol v2 §3")
        a.save_answer(dataset, "DEP-003", "Unknown")
        old = a.get_answers(dataset)
        expected = {
            "dataset_name_version": "Dataset v1", "role": ["Other", "Training"],
            "role_other": "Calibration", "source_documentation": "Protocol v2 §3",
        }
        self.assertEqual(a.native_profile()["datasets"][0]["DEP-001"], expected)
        for field, value in (
            ("DEP-001.role", ["External"]), ("DEP-001.role", ["Training", "Training"]),
            ("DEP-001.role", "Training"), ("DEP-001.source_documentation", []),
            ("DEP-003", "Select an option"), ("DEP-003", 1), ("DEP-999", "Unknown"),
            ("DEP-019-versions", "Wrong record"), ("DEP-015-details", "Inactive"),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                a.save_answer(dataset, field, value)
        self.assertEqual(a.get_answers(dataset), old)
        self.assertTrue(any(i["field_id"] == "DEP-003" and i["type"] == "uncertain"
                            for i in a.validate_record(dataset)))
        a.save_answer(dataset, "DEP-001.role", ["Training"])
        self.assertNotIn("DEP-001.role_other", a.get_answers(dataset))
        self.assertEqual(a.get_answers(dataset)["DEP-001.source_documentation"], "Protocol v2 §3")
        self.assertIsNone(a.native_profile()["datasets"][0]["DEP-001"]["role_other"])

    def test_dep012_explicit_trigger_and_independent_expert_role(self):
        a = self.adapter
        dataset = a.create_record("dataset")
        self.assertNotIn("DEP-012-trigger", a.native_profile()["datasets"][0])
        a.save_answer(dataset, "DEP-012-trigger", "Yes")
        self.assertIn("DEP-012", a.active_fields(dataset))
        self.assertNotIn("DEP-012", a.get_answers(dataset))
        self.assertTrue(any(issue["field_id"] == "DEP-012" and issue["type"] == "conditional"
                            for issue in a.validate_record(dataset)))
        a.save_answer(dataset, "DEP-012", "Two independent readers")
        a.save_answer(dataset, "DEP-011", ["Expert read"])
        a.save_answer(dataset, "DEP-012-trigger", "No")
        native = a.native_profile()["datasets"][0]
        self.assertEqual(native["DEP-012-trigger"], "No")
        self.assertEqual(native["DEP-012"], "Two independent readers")
        a.save_answer(dataset, "DEP-011", ["Pathology"])
        self.assertNotIn("DEP-012", a.get_answers(dataset))
        self.assertNotIn("DEP-012", a.active_fields(dataset))

    def test_dep028_visibility_is_separate_from_validation(self):
        a = self.adapter
        function = a.create_record("function")
        a.save_answer(function, "DEP-028", ["Literature only"])
        self.assertIn("DEP-029-population", a.active_fields(function))
        self.assertNotIn("DEP-029-population", a.get_answers(function))
        findings = {issue["field_id"] for issue in a.validate_record(function)}
        self.assertNotIn("DEP-029-population", findings)
        self.assertIn("DEP-033", findings)
        a.save_answer(function, "DEP-029-population", "Reported cohort")
        a.save_answer(function, "DEP-030-measures", ["Other"])
        a.save_answer(function, "DEP-030-other", "AUC")
        a.save_answer(function, "DEP-028", ["Reader study"])
        self.assertIn("DEP-029-population", a.get_answers(function))
        self.assertTrue(any(issue["field_id"] == "DEP-030-results"
                            for issue in a.validate_record(function)))
        a.save_answer(function, "DEP-028", ["None yet"])
        self.assertEqual(a.get_answers(function), {"DEP-028": ["None yet"]})
        self.assertIsNone(a.native_profile()["ai_function_versions"][0]["DEP-030-results"])

    def test_gmlp_and_native_manual_parity(self):
        a = self.adapter
        dataset = a.create_record("dataset")
        function = a.create_record("function")
        a.save_answer(dataset, "DEP-001.dataset_name_version", "Study set v2")
        a.save_answer(dataset, "DEP-001.role", ["Training", "Other"])
        a.save_answer(dataset, "DEP-001.role_other", "Calibration")
        a.save_answer(dataset, "DEP-015", "Yes")
        a.save_answer(function, "DEP-028", ["Literature only"])
        document = a.create_record("document")
        a.save_answer(document, "document_id", "Report-7")
        a.save_answer(document, "page_section", "§4")
        a.save_answer(document, "supported_fields", "DEP-025, DEP-036")
        a.save_answer(a.GMLP, "DEP-036-trigger", "Yes")
        a.save_answer(a.GMLP, "DEP-036", "Partly")
        self.assertTrue(any(i["field_id"] == "DEP-036" for i in a.validate_record(a.GMLP)))
        a.save_answer(a.GMLP, "DEP-036-document", "Report-7, §4")
        app = AppTest.from_string(
            "import streamlit as st\n"
            "from app.deliverable_2.questionnaires.Dataset_and_evidence import render_dataset_evidence\n"
            "st.session_state.native_profile = render_dataset_evidence()\n",
            default_timeout=25,
        ).run()
        app.text_input(key="document-0-id").set_value("Report-7")
        app.text_input(key="document-0-page-section").set_value("§4")
        app.text_input(key="document-0-supported-fields").set_value("DEP-025, DEP-036")
        app.text_input(key="dataset-0-DEP-001-name").set_value("Study set v2")
        app.multiselect(key="dataset-0-DEP-001-role").set_value(["Training", "Other"])
        app.selectbox(key="dataset-0-DEP-015").select("Yes")
        app.multiselect(key="function-0-DEP-028").set_value(["Literature only"])
        app.selectbox(key="DEP-036-trigger").select("Yes").run()
        app.text_input(key="dataset-0-DEP-001-role-other").set_value("Calibration")
        app.selectbox(key="DEP-036").select("Partly").run()
        app.text_input(key="DEP-036-document").set_value("Report-7, §4").run()
        self.assertFalse(app.exception)
        self.assertEqual(a.native_profile(), app.session_state.native_profile)
        self.assertEqual(a.validate(), validate_dataset_evidence(app.session_state.native_profile))
        self.assertEqual(a.native_profile()["datasets"][0]["DEP-015-details"], "")
        self.assertIsNone(a.native_profile()["ai_function_versions"][0]["DEP-024-details"])
        a.save_answer(a.GMLP, "DEP-036-trigger", "No")
        self.assertEqual(a.get_answers(a.GMLP), {"DEP-036-trigger": "No"})
        self.assertIsNone(a.native_profile()["DEP-036-document"])


class D24MetadataTests(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        self.owner = directory / SOURCE.name
        self.manifest = directory / MANIFEST.name
        self.source = SOURCE.read_bytes()

    def load_fixture(self, source, *, reviewed=False):
        self.assertNotEqual(source, self.source)
        self.owner.write_bytes(source)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        if reviewed:
            # Test fixture only. Production never updates the approved fingerprint.
            manifest["source_sha256"] = sha256(source).hexdigest()
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        return load_metadata(self.owner, self.manifest)

    def test_widget_key_rename_preserves_native_field_after_review(self):
        source = self.source.replace(b'key=f"dataset-{i}-DEP-003"', b'key=f"dataset-{i}-collection-design"')
        with self.assertRaisesRegex(D24CompatibilityError, "fingerprint changed"):
            self.load_fixture(source)
        metadata = self.load_fixture(source, reviewed=True)
        with patch("app.chatbot.d24_adapter.load_metadata", return_value=metadata):
            adapter = D24AnswerAdapter()
        dataset = adapter.create_record("dataset")
        adapter.save_answer(dataset, "DEP-003", "Mixed")
        self.assertEqual(adapter.native_profile()["datasets"][0]["DEP-003"], "Mixed")
        with self.assertRaisesRegex(ValueError, "Unknown or inactive"):
            adapter.save_answer(dataset, "collection-design", "Mixed")

    def test_unreviewed_source_changes_fail_closed(self):
        for old, new in (
            (b'dataset["DEP-003"] =', b'dataset["DEP-903"] ='),
            (b'"Mixed",', b'"Combined",'),
            (b'if dataset["DEP-015"] == "Yes":', b'if dataset["DEP-015"] == "No":'),
            (b'# MAIN QUESTIONNAIRE', b'# OWNER QUESTIONNAIRE'),
        ):
            with self.subTest(change=new), self.assertRaisesRegex(
                D24CompatibilityError, r"compatibility manifest requires review.*fingerprint changed"
            ):
                self.load_fixture(self.source.replace(old, new))
            self.assertEqual(json.loads(self.manifest.read_text()), json.loads(MANIFEST.read_text()))

    def test_unsupported_semantic_syntax_fails_even_with_matching_fingerprint(self):
        for old, new in (
            (b'dataset["DEP-003"] =', b'dataset[make_field_id()] ='),
            (b'if dataset["DEP-015"] == "Yes":', b'if infer_applicability(dataset):'),
            (b'key=f"dataset-{i}-DEP-003",', b'key=f"dataset-{i}-DEP-003", index=1,'),
        ):
            with self.subTest(change=new), self.assertRaisesRegex(D24CompatibilityError, "unsupported"):
                self.load_fixture(self.source.replace(old, new), reviewed=True)

    def test_renderer_source_is_never_executed(self):
        marker = self.owner.with_suffix(".executed")
        sentinel = f"\nopen({str(marker)!r}, 'w').close()\n".encode()
        with self.assertRaisesRegex(D24CompatibilityError, "unsupported Expr"):
            self.load_fixture(self.source + sentinel, reviewed=True)
        self.assertFalse(marker.exists())
        with patch.dict("sys.modules", {
            "app.deliverable_2.questionnaires.Dataset_and_evidence": None,
        }), patch.object(st, "session_state", None):
            adapter = D24AnswerAdapter()
            record = adapter.create_record("dataset")
            self.assertEqual(adapter.active_fields(record), adapter.active_fields(record))
            adapter.save_answer(record, "DEP-003", "Unknown")
            adapter.validate()
            self.assertEqual(adapter.native_profile()["datasets"][0]["DEP-003"], "Unknown")

    def test_invalid_manifest_has_safe_diagnostic_and_no_catalogue(self):
        self.owner.write_bytes(self.source)
        self.manifest.write_text("{invalid private fixture text")
        with self.assertRaisesRegex(D24CompatibilityError, "compatibility manifest requires review") as failure:
            load_metadata(self.owner, self.manifest)
        self.assertNotIn("private fixture", str(failure.exception))
        self.assertTrue(failure.exception.__suppress_context__)
        self.assertEqual(self.manifest.read_text(), "{invalid private fixture text")
