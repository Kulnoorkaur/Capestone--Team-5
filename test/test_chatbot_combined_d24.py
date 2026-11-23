from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.d23_adapter import D23AnswerAdapter
from app.chatbot.d24_adapter import D24AnswerAdapter
from app.chatbot.d24_metadata import D24CompatibilityError, MANIFEST, SOURCE
from app.chatbot.profile_io import (
    ProfileImportError,
    dump_combined_profile,
    load_combined_profile,
    load_confirmed_profile,
)
from app.chatbot.questionnaire_bridge import QuestionnaireBridge


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"


def sample_backup():
    bridge = QuestionnaireBridge()
    bridge.save_answer("PIP-001", "Demo product")
    bridge.save_answer("AIF-019", "No")
    algorithms = D23AnswerAdapter()
    for algorithm_id in ("algorithm-7", "algorithm-8"):
        algorithms.add_algorithm("Shared model name", "1", algorithm_id=algorithm_id)
        algorithms.save_answer(algorithm_id, "ACC-001", f"Model {algorithm_id}", evidence="Model register")
    d24 = D24AnswerAdapter()
    for record_id in ("dataset-11", "dataset-12"):
        d24.create_record("dataset", record_id=record_id)
        d24.save_answer(record_id, "DEP-001.dataset_name_version", "Shared dataset name")
    d24.save_answer("dataset-11", "DEP-001.role", ["Other"])
    d24.save_answer("dataset-11", "DEP-001.role_other", "Calibration")
    d24.save_answer("dataset-11", "DEP-012-trigger", "Yes")
    d24.save_answer("dataset-11", "DEP-012", "Two reviewers")
    d24.save_answer("dataset-12", "DEP-003", "Unknown")
    for record_id, value in (("function-13", ["Literature only"]), ("function-14", ["Reader study"])):
        d24.create_record("function", record_id=record_id)
        d24.save_answer(record_id, "DEP-019-versions", record_id)
        d24.save_answer(record_id, "DEP-028", value)
    d24.save_answer("function-13", "DEP-033", "Literature summary")
    d24.save_answer("function-14", "DEP-030-results", "Recorded results")
    for record_id in ("document-15", "document-16"):
        d24.create_record("document", record_id=record_id)
        d24.save_answer(record_id, "title", "Shared document title")
        d24.save_answer(record_id, "document_id", f"Evidence {record_id}")
        d24.save_answer(record_id, "version", "v1")
        d24.save_answer(record_id, "date", "2026-11-01")
        d24.save_answer(record_id, "page_section", "Section 4")
        d24.save_answer(record_id, "supported_fields", "DEP-028, DEP-036")
    d24.save_answer(d24.GMLP, "DEP-036-trigger", "Yes")
    d24.save_answer(d24.GMLP, "DEP-036", "Partly")
    d24.save_answer(d24.GMLP, "DEP-036-document", "Evidence document-15, §4")
    return bridge, algorithms, d24


class D24CombinedProfileTests(unittest.TestCase):
    def test_empty_and_partial_profiles_remain_valid(self):
        bridge, algorithms, d24 = QuestionnaireBridge(), D23AnswerAdapter(), D24AnswerAdapter()
        raw = dump_combined_profile(bridge, dataset_evidence=d24)
        self.assertEqual(json.loads(raw)["version"], 2)
        restored = load_combined_profile(raw, allow_d24=True)
        self.assertEqual(restored.bridge.get_product_profile(), {})
        self.assertEqual(restored.algorithms.algorithm_ids, ())
        self.assertEqual(restored.dataset_evidence.get_answers(d24.GMLP), {})
        for kind in ("dataset", "function", "document"):
            self.assertEqual(restored.dataset_evidence.record_ids(kind), ())
        d24.create_record("dataset")
        algorithms.add_algorithm("Partial algorithm")
        restored = load_combined_profile(dump_combined_profile(bridge, algorithms, dataset_evidence=d24), allow_d24=True)
        self.assertEqual(restored.dataset_evidence.get_answers("dataset-1"), {})
        self.assertEqual(restored.algorithms.algorithm_ids, ("algorithm-1",))

    def test_round_trip_preserves_only_confirmed_answers_and_ids(self):
        bridge, algorithms, d24 = sample_backup()
        raw = dump_combined_profile(bridge, algorithms, dataset_evidence=d24)
        payload = json.loads(raw)
        self.assertEqual(payload["dataset_evidence"]["datasets"][0]["answers"]["DEP-001"], {
            "dataset_name_version": "Shared dataset name", "role": ["Other"], "role_other": "Calibration",
        })
        self.assertNotIn("DEP-012", payload["dataset_evidence"]["datasets"][1]["answers"])
        restored = load_combined_profile(raw.encode(), allow_d24=True)
        self.assertEqual(restored.bridge.get_product_profile(), {"PIP-001": "Demo product", "AIF-019": "No"})
        self.assertEqual(restored.algorithms.algorithm_ids, ("algorithm-7", "algorithm-8"))
        self.assertEqual(restored.dataset_evidence.native_profile(), d24.native_profile())
        self.assertEqual(restored.dataset_evidence.validate(), d24.validate())
        self.assertEqual(json.loads(dump_combined_profile(
            restored.bridge, restored.algorithms, dataset_evidence=restored.dataset_evidence,
        )), payload)
        for kind in ("dataset", "function", "document"):
            self.assertEqual(restored.dataset_evidence.record_ids(kind), d24.record_ids(kind))
        self.assertEqual(restored.dataset_evidence.create_record("dataset"), "dataset-17")
        for section in ("datasets", "ai_function_versions", "evidence_documents"):
            self.assertTrue(all("record_id" not in record for record in d24.native_profile()[section]))

    def test_v1_and_flat_formats_are_still_supported(self):
        bridge, algorithms, d24 = sample_backup()
        v1 = dump_combined_profile(bridge, algorithms)
        self.assertEqual(json.loads(v1)["version"], 1)
        self.assertIsNone(load_combined_profile(v1, allow_d24=True).dataset_evidence)
        raw = dump_combined_profile(bridge, algorithms, dataset_evidence=d24)
        with self.assertRaisesRegex(ProfileImportError, "Unsupported combined profile version"):
            load_combined_profile(raw)
        self.assertEqual(load_confirmed_profile('{"AIF-019":"No"}'), {"product": {}, "ai_function": {"AIF-019": "No"}})

    def test_invalid_profiles_are_rejected_atomically(self):
        bridge, algorithms, adapter = sample_backup()
        payload = json.loads(dump_combined_profile(bridge, algorithms, dataset_evidence=adapter))
        cases = (
            ("datasets", 0, {"DEP-999": "Unknown"}, "Unknown field IDs"),
            ("datasets", 0, {"DEP-003": []}, "Expected an allowed option"),
            ("datasets", 0, {"DEP-003": "Unsupported option"}, "Expected an allowed option"),
            ("datasets", 0, {"DEP-001": {"role": "Training"}}, "Expected a non-empty list"),
            ("datasets", 0, {"DEP-001": {"role_other": "Inactive"}}, "Unknown or inactive"),
            ("datasets", 0, {"DEP-012": "Untriggered"}, "Unknown or inactive"),
            ("ai_function_versions", 0, {"DEP-028": ["Unknown"], "DEP-033": "Inactive"}, "Unknown or inactive"),
            ("evidence_documents", 1, {"version": 3}, "Expected non-empty text"),
        )
        for collection, index, answers, message in cases:
            with self.subTest(collection=collection, answers=answers):
                invalid = deepcopy(payload)
                invalid["dataset_evidence"][collection][index]["answers"] = answers
                with self.assertRaisesRegex(ProfileImportError, message):
                    load_combined_profile(json.dumps(invalid), allow_d24=True)
        invalid = deepcopy(payload)
        invalid["dataset_evidence"]["gmlp"]["DEP-036-trigger"] = "No"
        with self.assertRaisesRegex(ProfileImportError, "D2.4 GMLP.*Unknown or inactive"):
            load_combined_profile(json.dumps(invalid), allow_d24=True)
        for collection in ("datasets", "ai_function_versions", "evidence_documents"):
            invalid = deepcopy(payload)
            records = invalid["dataset_evidence"][collection]
            records[1]["record_id"] = records[0]["record_id"]
            with self.assertRaisesRegex(ProfileImportError, "Duplicate D2.4 record ID"):
                load_combined_profile(json.dumps(invalid), allow_d24=True)
        for raw, error in (("{", "Invalid JSON"), (json.dumps({**payload, "version": 9}), "Unsupported combined")):
            with self.assertRaisesRegex(ProfileImportError, error):
                load_combined_profile(raw, allow_d24=True)
        with patch("app.chatbot.d24_adapter.load_metadata", side_effect=D24CompatibilityError("Source changed.")):
            with self.assertRaisesRegex(ProfileImportError, "manifest requires review"):
                load_combined_profile(json.dumps(payload), allow_d24=True)
        payload["dataset_evidence"]["questionnaire_sha256"] = "different-source"
        with self.assertRaisesRegex(ProfileImportError, "different questionnaire fingerprint"):
            load_combined_profile(json.dumps(payload), allow_d24=True)


class D24CombinedProfileStreamlitTests(unittest.TestCase):
    def setUp(self):
        gemini = self.enterContext(patch.object(
            chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")
        ))
        self.addCleanup(gemini.assert_not_called)
        self.app = AppTest.from_file(str(CHAT_APP), default_timeout=30).run()
        self.state = self.app.session_state
        self.state.questionnaire_complete = True
        self.state.questionnaire_bridge.save_answer("PIP-001", "Existing product")
        self.state.questionnaire_bridge.save_answer("AIF-019", "Yes")
        old = D23AnswerAdapter()
        algorithm_id = old.add_algorithm("Existing algorithm")
        old.save_answer(algorithm_id, "ACC-001", "Existing model", evidence="Existing model register")
        self.state.d23_adapter = old
        self.state.d23_answer_revision = 0
        self.app.run()
        self.click("Continue with gaps")
        self.click("Continue with gaps")
        self.click("Add dataset")
        self.old_d24 = self.state.d24_adapter
        self.old_id = self.old_d24.selected_record_id
        self.app.text_area(key=f"d24-answer-{self.old_id}-DEP-001.dataset_name_version-0").set_value("Existing dataset")
        self.click("Confirm D2.4 answer")
        evaluation = self.old_d24.create_record("function")
        self.old_d24.save_answer(evaluation, "DEP-019-versions", "Existing evaluation")
        document = self.old_d24.create_record("document")
        self.old_d24.save_answer(document, "document_id", "Existing evidence")
        self.old_d24.save_answer(self.old_d24.GMLP, "DEP-036-trigger", "No")

    def click(self, label):
        next(button for button in self.app.button if button.label == label).click().run()
        self.assertFalse(self.app.exception, [error.message for error in self.app.exception])
        if label == "Continue with gaps":
            self.click("Confirm continue with gaps")

    def upload(self, raw):
        self.app.file_uploader(key="profile_upload").set_value(
            ("combined.json", raw.encode(), "application/json"),
        ).run()
        self.assertFalse(self.app.exception, [error.message for error in self.app.exception])

    def test_invalid_v2_uploads_preserve_all_active_stores_and_selections(self):
        bridge, algorithms, d24 = sample_backup()
        payload = json.loads(dump_combined_profile(bridge, algorithms, dataset_evidence=d24))
        manifest = MANIFEST.read_bytes()
        self.assertEqual(payload["dataset_evidence"]["questionnaire_sha256"], sha256(SOURCE.read_bytes()).hexdigest())
        self.state["d24-picker-function"] = self.old_d24.record_ids("function")[0]
        self.state["d24-picker-document"] = self.old_d24.record_ids("document")[0]
        existing_bridge = self.state.questionnaire_bridge
        existing_algorithms = self.state.d23_adapter
        existing_native = self.old_d24.native_profile()
        existing_picks = {key: self.state[key] for key in (
            "d24-picker-dataset", "d24-picker-function", "d24-picker-document",
        )}
        cases = (
            (("dataset_evidence", "datasets", 0, "answers", "DEP-999"), "Unknown", "Unknown field IDs"),
            (("dataset_evidence", "datasets", 0, "answers", "DEP-003"), "Invalid", "allowed option"),
            (("dataset_evidence", "datasets", 1, "answers", "DEP-012"), "Untriggered", "inactive field"),
            (("dataset_evidence", "datasets", 1, "record_id"), "dataset-11", "Duplicate D2.4 record ID"),
            (("dataset_evidence", "questionnaire_sha256"), "unreviewed", "compatibility manifest requires review"),
            (("algorithms", 1, "name"), [], "Algorithm record 2"),
            (("product", "PIP-001"), [], "PIP-001"),
            (("ai_function", "AIF-019"), "Invalid", "AIF-019"),
        )
        for path, value, diagnostic in cases:
            with self.subTest(path=path):
                invalid = deepcopy(payload)
                destination = invalid
                for key in path[:-1]:
                    destination = destination[key]
                destination[path[-1]] = value
                self.upload(json.dumps(invalid))
                self.assertTrue(any(diagnostic in error.value for error in self.app.error))
                self.assertNotIn("Restore combined profile", [button.label for button in self.app.button])
                self.assertIs(self.state.questionnaire_bridge, existing_bridge)
                self.assertEqual(existing_bridge.get_product_profile(), {"PIP-001": "Existing product", "AIF-019": "Yes"})
                self.assertIs(self.state.d23_adapter, existing_algorithms)
                self.assertEqual(existing_algorithms.algorithm_ids, ("algorithm-1",))
                self.assertEqual(existing_algorithms.get_algorithm("algorithm-1")["answers"]["ACC-001"]["value"],
                                 "Existing model")
                self.assertIs(self.state.d24_adapter, self.old_d24)
                self.assertEqual(self.old_d24.native_profile(), existing_native)
                self.assertEqual(self.old_d24.selected_record_id, self.old_id)
                self.assertEqual({key: self.state[key] for key in existing_picks}, existing_picks)
        self.assertEqual(MANIFEST.read_bytes(), manifest)

    def test_v2_fresh_session_round_trip_without_renderer(self):
        bridge, algorithms, d24 = sample_backup()
        with patch.dict("sys.modules", {"app.deliverable_2.questionnaires.Dataset_and_evidence": None}):
            raw = dump_combined_profile(bridge, algorithms, dataset_evidence=d24)
            fresh = AppTest.from_file(str(CHAT_APP), default_timeout=30).run()
            fresh.file_uploader(key="profile_upload").set_value(
                ("combined.json", raw.encode(), "application/json"),
            ).run()
            self.assertNotIn("d24_adapter", fresh.session_state)
            next(button for button in fresh.button if button.label == "Restore combined profile").click().run()
            self.assertFalse(fresh.exception)
            with patch.object(st, "download_button", wraps=st.download_button) as downloads:
                fresh.run()
            exported = next(call.kwargs["data"] for call in downloads.call_args_list
                            if call.args[0] == "Download Profile")
        self.assertEqual(json.loads(exported), json.loads(raw))

    def test_v2_preview_atomic_failure_and_explicit_restore_clear_old_review(self):
        bridge, algorithms, d24 = sample_backup()
        raw = dump_combined_profile(bridge, algorithms, dataset_evidence=d24)
        invalid = json.loads(raw)
        invalid["dataset_evidence"]["evidence_documents"][-1]["answers"]["version"] = []
        self.state.d24_conversations[self.old_id]["pending"]["DEP-003"] = {
            "source_id": "1", "value": "Mixed", "quote": "Old confidential quote", "explanation": "Old model explanation",
        }
        self.state.d24_conversations[self.old_id]["turns"].append("Old chat turn")
        self.state["d24-picker-function"] = "function-stale"
        self.state["d24-picker-document"] = "document-stale"
        self.state.retryable_turn = {"message": "Old retry", "context": ("D2.1", None, None), "source_id": "1"}
        draft = f"d24-answer-{self.old_id}-DEP-001.role-1"
        self.app.multiselect(key=draft).set_value(["Training"]).run()
        self.state.unrelated = "Keep"
        self.upload(json.dumps(invalid))
        self.assertTrue(any("evidence_documents record 2" in item.value for item in self.app.error))
        self.assertNotIn("Restore combined profile", [button.label for button in self.app.button])
        self.assertIs(self.state.d24_adapter, self.old_d24)
        self.assertEqual(self.old_d24.selected_record_id, self.old_id)
        self.assertEqual(self.state.questionnaire_bridge.get_product_profile(), {"PIP-001": "Existing product", "AIF-019": "Yes"})
        self.assertEqual(self.state.d23_adapter.algorithm_ids, ("algorithm-1",))
        self.assertIn("DEP-003", self.state.d24_conversations[self.old_id]["pending"])
        self.upload(raw)
        self.assertIs(self.state.d24_adapter, self.old_d24)
        self.assertEqual(self.old_d24.selected_record_id, self.old_id)
        self.assertTrue(any("2 datasets, 2 evaluations, 2 documents" in item.value for item in self.app.caption))
        self.assertTrue(any("2 algorithm records" in item.value for item in self.app.caption))
        stale = next(button for button in self.app.button if (button.key or "").startswith("d24-review-")
                     and button.key.endswith("-confirm"))
        stale.click()
        self.click("Restore combined profile")
        restored = self.state.d24_adapter
        self.assertIsNot(restored, self.old_d24)
        self.assertEqual(restored.native_profile(), d24.native_profile())
        self.assertIsNone(restored.selected_record_id)
        self.assertEqual(self.state.d24_conversations, {})
        self.assertEqual(self.state.d24_revisions, {})
        self.assertIsNone(self.state.retryable_turn)
        for key in ("d24-section", "d24-picker-dataset", "d24-picker-function", "d24-picker-document", stale.key, draft):
            self.assertNotIn(key, self.state)
        self.assertEqual(self.state.unrelated, "Keep")
        self.assertFalse(any("DEP-003" in self.old_d24.get_answers(record) for record in self.old_d24.record_ids("dataset")))
        with patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.app.run()
        exported = next(call.kwargs["data"] for call in downloads.call_args_list
                        if call.args[0] == "Download Profile")
        self.assertEqual(json.loads(exported), json.loads(raw))
        for excluded in ("Old confidential quote", "Old chat turn", "Old model explanation", "source_id", "timestamp"):
            self.assertNotIn(excluded, exported)

    def test_v1_restore_preserves_d24_session_answers(self):
        bridge, algorithms, _ = sample_backup()
        self.state.d24_conversations[self.old_id]["pending"]["DEP-003"] = {
            "source_id": "1", "value": "Mixed", "quote": "Pending quote", "explanation": "",
        }
        question = f"d24-question-{self.old_id}-1"
        self.app.selectbox(key=question).select("DEP-002").run()
        draft = f"d24-answer-{self.old_id}-DEP-002-1"
        self.app.text_area(key=draft).set_value("Unconfirmed location").run()
        snapshot = self.old_d24.native_profile()
        self.upload(dump_combined_profile(bridge, algorithms))
        self.assertIn(
            "This version 1 backup contains D2.1–D2.3 only. Restoring it will replace those sections "
            "and preserve your current D2.4 answers.",
            [item.value for item in self.app.warning],
        )
        self.click("Restore combined profile")
        self.assertIs(self.state.d24_adapter, self.old_d24)
        self.assertEqual(self.old_d24.selected_record_id, self.old_id)
        self.assertEqual(self.old_d24.get_answers(self.old_id), {"DEP-001.dataset_name_version": "Existing dataset"})
        self.assertEqual(self.old_d24.native_profile(), snapshot)
        self.assertIn("DEP-003", self.state.d24_conversations[self.old_id]["pending"])
        self.assertEqual(self.app.text_area(key=draft).value, "Unconfirmed location")
        self.assertEqual(self.state.questionnaire_bridge.get_product_profile(), bridge.get_product_profile())
        self.assertEqual(self.state.d23_adapter.algorithm_ids, algorithms.algorithm_ids)
