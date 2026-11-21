import json
from pathlib import Path
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.questionnaire_bridge import QUESTIONNAIRE_FIELDS
from app.deliverable_2.questionnaires.algorithm_change_control import (
    ADAPTIVE,
    BY_ID,
    FRAMEWORKS,
    needs_details,
)


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"


class D23ChatTests(unittest.TestCase):
    def setUp(self):
        gemini = patch.object(chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call"))
        self.gemini = gemini.start()
        self.addCleanup(gemini.stop)
        self.addCleanup(self.gemini.assert_not_called)
        self.app = AppTest.from_file(str(CHAT_APP), default_timeout=30).run()
        self.assert_no_errors()

    def assert_no_errors(self):
        self.assertFalse(self.app.exception, [error.message for error in self.app.exception])

    def button(self, label):
        return next(button for button in self.app.button if button.label == label)

    def click(self, label):
        self.button(label).click().run()
        self.assert_no_errors()

    def finish_d22(self):
        bridge = self.app.session_state.questionnaire_bridge
        for questionnaire, fields in QUESTIONNAIRE_FIELDS.items():
            for field_id in fields:
                if field_id == "AIF-020":
                    continue
                options = bridge.get_field_options(field_id)
                value = options[0] if options else "Demo product detail"
                if bridge.get_field_type(field_id) == "multiselect":
                    value = [value]
                self.assertTrue(bridge.save_answer(field_id, value)[0])
            for field_id in bridge.get_active_conditional_fields(questionnaire):
                self.assertTrue(bridge.save_answer(field_id, "Demo follow-up")[0])

        self.app.session_state.intake_started = True
        self.app.session_state.asked_field = "AIF-020"
        self.app.session_state.asked_question = "How does the system handle inadequate input?"
        self.app.run()
        self.assert_no_errors()
        self.assertNotIn("Continue to D2.3", [button.label for button in self.app.button])
        self.app.multiselect(key="manual_AIF-020_0").set_value(["Reject input"])
        self.app.button(key="save_manual_AIF-020").click().run()
        self.assert_no_errors()
        self.assertTrue(self.app.session_state.questionnaire_complete)
        self.click("Continue to D2.3")

    def add_algorithm(self, name, version):
        self.app.text_input(key="d23-new-name").set_value(name)
        self.app.text_input(key="d23-new-version").set_value(version)
        self.click("Add algorithm")
        return self.app.session_state.d23_active_algorithm_id

    def answer_key(self, field_id):
        key = self.button("Confirm D2.3 answer").key.removesuffix("-confirm")
        self.assertIn(f"-{field_id}-", key)
        return key

    def set_answer(self, field_id, value):
        key = self.answer_key(field_id)
        field_type = BY_ID[field_id]["type"]
        if field_type == "text":
            self.app.text_input(key=key).set_value(value)
        elif field_type == "longtext":
            self.app.text_area(key=key).set_value(value)
        elif field_type == "select":
            self.app.selectbox(key=key).select(value)
        elif field_type == "multiselect":
            self.app.multiselect(key=key).set_value(value)
        else:
            for framework, status in value.items():
                self.app.selectbox(key=f"{key}-{framework}").select(status)
        return key

    def revise(self, algorithm_id, field_id):
        revision = self.app.session_state.d23_answer_revision
        picker = self.app.selectbox(key=f"d23-revise-{algorithm_id}-{revision}")
        picker.select(field_id).run()
        self.assert_no_errors()

    def send_stale_confirmation(self, widget_id):
        # Simulate an old browser event arriving after its button was removed.
        events = self.app._tree.get_widget_states()
        events.widgets.add(id=widget_id, trigger_value=True)
        self.app._run(widget_state=events, timeout=30)
        self.assert_no_errors()

    def assert_flat_download(self, expected):
        with patch.object(st, "download_button", wraps=st.download_button) as downloads:
            self.app.run()
        self.assert_no_errors()
        [download] = [call.kwargs for call in downloads.call_args_list
                      if call.args and call.args[0] == "Export Confirmed Profile"]
        self.assertEqual(download["file_name"], "regulatory_d21_d22_profile.json")
        self.assertEqual(json.loads(download["data"]), expected)

    def test_entry_identity_selection_and_legacy_profile_compatibility(self):
        self.finish_d22()
        first = self.add_algorithm("Screening model", "1.0")
        adapter = self.app.session_state.d23_adapter
        self.assertEqual(adapter.get_algorithm(first)["answers"], {})
        key = self.set_answer("ACC-001", "Screening model 1.0")
        self.app.text_area(key=f"{key}-details").set_value("Screening model release")
        self.app.text_input(key=f"{key}-evidence").set_value("Screening release record")
        self.app.run()
        self.assert_no_errors()
        self.assertEqual(adapter.get_algorithm(first)["answers"], {})
        self.click("Confirm D2.3 answer")

        second = self.add_algorithm("Triage model", "2.0")
        self.assertNotEqual(first, second)
        key = self.set_answer("ACC-001", "Triage model 2.0")
        self.app.text_input(key=f"{key}-evidence").set_value("Triage release record")
        self.click("Confirm D2.3 answer")
        self.set_answer("ACC-002", "AIF-004")
        self.click("Confirm D2.3 answer")
        self.app.selectbox(key="d23-algorithm-picker").select(first).run()
        self.assert_no_errors()
        self.assertEqual(self.app.session_state.d23_active_algorithm_id, first)
        self.answer_key("ACC-002")

        self.app.text_input(key=f"d23-name-{first}").set_value("Renamed screening model")
        self.app.text_input(key=f"d23-version-{first}").set_value("1.1")
        self.click("Save algorithm identity")
        self.assertEqual(adapter.algorithm_ids, (first, second))
        self.assertEqual(adapter.get_algorithm(first)["name"], "Renamed screening model")
        self.assertEqual(adapter.get_algorithm(first)["version"], "1.1")
        self.assertEqual(adapter.get_algorithm(first)["answers"]["ACC-001"], {
            "value": "Screening model 1.0",
            "details": "Screening model release",
            "evidence": "Screening release record",
        })
        self.assertEqual(adapter.get_algorithm(second)["answers"]["ACC-001"]["value"], "Triage model 2.0")
        self.assertEqual(adapter.get_algorithm(second)["answers"]["ACC-001"]["evidence"], "Triage release record")

        self.app.selectbox(key="d23-algorithm-picker").select(second).run()
        self.assertEqual(self.app.session_state.d23_active_algorithm_id, second)
        flat = self.app.session_state.questionnaire_bridge.get_product_profile()
        self.assert_flat_download(flat)
        self.click("Back to D2.1 and D2.2")
        self.assertEqual(adapter.algorithm_ids, (first, second))
        self.assertTrue(self.app.chat_input)
        self.click("Continue to D2.3")
        self.assertEqual(self.app.session_state.d23_active_algorithm_id, second)
        self.answer_key("ACC-003")

        self.app.file_uploader(key="restore_profile_upload").set_value(
            ("profile.json", json.dumps(flat).encode(), "application/json")
        ).run()
        self.click("Restore from JSON")
        self.assertTrue(self.app.chat_input)
        self.assertEqual(adapter.algorithm_ids, (first, second))
        self.assert_flat_download(flat)
        self.click("Start New Assessment")
        self.assertNotIn("d23_adapter", self.app.session_state)
        self.assertNotIn("d23_active_algorithm_id", self.app.session_state)

    def test_all_answer_types_and_nested_progression_with_parent_revision(self):
        self.finish_d22()
        algorithm_id = self.add_algorithm("Demo model", "1.0")
        adapter = self.app.session_state.d23_adapter
        values = {
            "ACC-002": "AIF-004",
            "ACC-005": "Unknown",
            "ACC-008": ADAPTIVE,
            "ACC-013": "Yes",
            "ACC-019": "Yes",
        }
        for field_id, definition in BY_ID.items():
            kind = definition["type"]
            if kind in ("text", "longtext"):
                value = f"Description for {field_id}"
            elif kind == "select":
                value = definition["options"][0]
            elif kind == "multiselect":
                value = definition["options"][:1]
            else:
                value = dict.fromkeys(FRAMEWORKS, "Not submitted")
            value = values.get(field_id, value)

            if field_id == "ACC-020":
                self.set_answer(field_id, {"FDA": "Not submitted"})
                self.click("Confirm D2.3 answer")
                partial = adapter.get_algorithm(algorithm_id)["answers"][field_id]["value"]
                self.assertEqual(partial["FDA"], "Not submitted")
                self.assertIsNone(partial["Health Canada"])

            key = self.set_answer(field_id, value)
            if needs_details(field_id, value):
                self.app.text_area(key=f"{key}-details").set_value("Reviewed explanation")
            self.app.text_input(key=f"{key}-evidence").set_value("Design record V1, §2")
            self.click("Confirm D2.3 answer")

        self.assertEqual(len(adapter.get_algorithm(algorithm_id)["answers"]), 29)
        self.assertTrue(any("29/29 applicable answers complete" in item.proto.text for item in self.app.get("progress")))
        confirmed = adapter.get_algorithm(algorithm_id)["answers"]
        self.assertEqual(confirmed["ACC-005"], {
            "value": "Unknown", "details": "Reviewed explanation", "evidence": "Design record V1, §2",
        })
        self.assertEqual(confirmed["ACC-020"]["value"], dict.fromkeys(FRAMEWORKS, "Not submitted"))

        self.revise(algorithm_id, "ACC-013")
        self.set_answer("ACC-013", "No")
        self.click("Confirm D2.3 answer")
        confirmed = adapter.get_algorithm(algorithm_id)["answers"]
        self.assertFalse(set(confirmed) & {f"ACC-{i:03}" for i in range(14, 21)})
        self.assertEqual(confirmed["ACC-013"]["value"], "No")
        self.assertEqual(confirmed["ACC-010"]["value"], "Description for ACC-010")
        self.revise(algorithm_id, "ACC-013")
        self.set_answer("ACC-013", "Yes")
        self.click("Confirm D2.3 answer")
        self.answer_key("ACC-014")

    def test_pending_answer_cannot_cross_algorithm_boundary(self):
        self.finish_d22()
        first = self.add_algorithm("Algorithm A", "1.0")
        adapter = self.app.session_state.d23_adapter
        self.click("Confirm D2.3 answer")
        second = self.add_algorithm("Algorithm B", "2.0")
        self.click("Confirm D2.3 answer")
        self.app.selectbox(key="d23-algorithm-picker").select(first).run()

        original_a = adapter.get_algorithm(first)
        original_b = adapter.get_algorithm(second)
        self.assertEqual(original_a["answers"]["ACC-001"]["details"], "")
        self.assertEqual(original_a["answers"]["ACC-001"]["evidence"], "")
        self.assertEqual(original_a["source_quotes"], {})
        key = self.set_answer("ACC-002", "AIF-004")
        self.app.text_area(key=f"{key}-details").set_value("Algorithm A detail")
        self.app.text_input(key=f"{key}-evidence").set_value("Algorithm A document")
        self.app.run()
        self.assert_no_errors()
        self.assertEqual(adapter.get_algorithm(first), original_a)
        confirm_a = self.button("Confirm D2.3 answer")

        # Send a pending click with the switch, then again after the rerun.
        self.app.selectbox(key="d23-algorithm-picker").select(second)
        confirm_a.click().run()
        self.assert_no_errors()
        self.assertEqual(self.app.session_state.d23_active_algorithm_id, second)
        self.send_stale_confirmation(confirm_a.id)
        self.assertEqual(adapter.get_algorithm(first), original_a)
        self.assertEqual(adapter.get_algorithm(second), original_b)

        key = self.set_answer("ACC-002", "AIF-006")
        self.assertEqual(self.app.text_area(key=f"{key}-details").value, "")
        self.assertEqual(self.app.text_input(key=f"{key}-evidence").value, "")
        self.app.run()
        self.assertEqual(adapter.get_algorithm(second), original_b)
        self.click("Confirm D2.3 answer")
        self.assertEqual(adapter.get_algorithm(second)["answers"]["ACC-002"], {
            "value": "AIF-006", "details": "", "evidence": "",
        })
        self.app.selectbox(key="d23-algorithm-picker").select(first).run()
        self.assert_no_errors()
        self.assertEqual(adapter.get_algorithm(first), original_a)

    def test_deactivated_pending_answer_and_revision_require_confirmation(self):
        self.finish_d22()
        algorithm_id = self.add_algorithm("Adaptive model", "1.0")
        adapter = self.app.session_state.d23_adapter
        prerequisites = {
            "ACC-001": "Adaptive model 1.0",
            "ACC-002": "AIF-004",
            "ACC-003": ["Supervised"],
            "ACC-004": ["CNN"],
            "ACC-005": "No",
            "ACC-006": "Yes",
            "ACC-007": "Fixed",
        }
        for field_id, value in prerequisites.items():
            adapter.save_answer(algorithm_id, field_id, value)
        self.app.run()
        self.set_answer("ACC-008", ADAPTIVE)
        self.click("Confirm D2.3 answer")
        self.set_answer("ACC-009", ["Model weights"])
        self.click("Confirm D2.3 answer")

        key = self.set_answer("ACC-010", "Unconfirmed learning mechanism")
        self.app.text_input(key=f"{key}-evidence").set_value("Unconfirmed mechanism document")
        self.app.run()
        self.assert_no_errors()
        stale_confirmation = self.button("Confirm D2.3 answer").id
        self.assertNotIn("ACC-010", adapter.get_algorithm(algorithm_id)["answers"])

        self.revise(algorithm_id, "ACC-008")
        self.set_answer("ACC-008", "Unknown")
        self.app.run()
        self.assert_no_errors()
        self.assertEqual(adapter.get_algorithm(algorithm_id)["answers"]["ACC-008"]["value"], ADAPTIVE)
        key = self.answer_key("ACC-008")
        self.app.text_area(key=f"{key}-details").set_value("Field behavior is still unknown.")
        self.click("Confirm D2.3 answer")
        self.assertNotIn("ACC-010", adapter.active_field_ids(algorithm_id))
        self.assertNotIn(stale_confirmation, [button.id for button in self.app.button])
        self.send_stale_confirmation(stale_confirmation)
        snapshot = adapter.get_algorithm(algorithm_id)
        self.assertNotIn("ACC-010", snapshot["answers"])
        self.assertNotIn("ACC-010", snapshot["source_quotes"])
        self.assertEqual(snapshot["answers"]["ACC-008"]["value"], "Unknown")

        # A sourced answer imported into the adapter must not become evidence
        # simply because its document-evidence input is shown for revision.
        adapter.save_answer(algorithm_id, "ACC-001", "Adaptive model 1.0",
                            source_quote="The model is called Adaptive model.")
        self.revise(algorithm_id, "ACC-001")
        key = self.answer_key("ACC-001")
        self.assertEqual(self.app.text_input(key=f"{key}-evidence").value, "")
        self.assertEqual(adapter.build_record(algorithm_id)["answers"]["ACC-001"]["evidence"], "")
        self.assertEqual(adapter.get_algorithm(algorithm_id)["source_quotes"]["ACC-001"],
                         "The model is called Adaptive model.")
