from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"


class GuidedConversationTests(unittest.TestCase):
    def setUp(self):
        gemini = self.enterContext(patch.object(
            chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")
        ))
        self.addCleanup(gemini.assert_not_called)
        self.app = AppTest.from_file(str(CHAT_APP), default_timeout=40).run()
        self.state = self.app.session_state
        self.state.questionnaire_complete = True
        self.app.run()
        self.click("Continue with gaps")

    def button(self, label):
        return next(item for item in self.app.button if item.label == label)

    def click(self, label):
        self.button(label).click().run()
        self.assertFalse(self.app.exception)

    def submit(self, key, text):
        self.app.chat_input(key=key).set_value(text).run()
        self.assertFalse(self.app.exception)

    def test_algorithm_conversation_creates_only_on_confirmation_and_saves_unknown_with_details(self):
        self.assertTrue(any("What is its name and version?" in item.value for item in self.app.markdown))
        adapter = self.state.d23_adapter
        self.assertEqual(adapter.algorithm_ids, ())
        self.submit("ux_d23_proposal-message", "Our algorithm is called Retina Reader version 2.5.")
        self.assertEqual(adapter.algorithm_ids, ())
        self.assertTrue(any(item.label == "Manage algorithms and answers" for item in self.app.expander))
        self.click("Confirm algorithm record")
        first = adapter.algorithm_ids[0]
        self.assertEqual(adapter.get_algorithm(first)["name"], "Retina Reader")
        self.assertEqual(adapter.get_algorithm(first)["version"], "2.5")
        self.assertEqual(adapter.get_algorithm(first)["answers"]["ACC-001"]["value"], "Retina Reader 2.5")
        self.assertTrue(any("Which AI function(s)" in item.value for item in self.app.markdown))
        self.assertFalse(any("AIF-004" in item.value for message in self.app.get("chat_message")
                             for item in message.get("markdown")))
        self.click("Skip for now")
        self.assertNotIn("ACC-002", adapter.get_algorithm(first)["answers"])
        self.click("Skip for now")
        self.click("I don't know")
        self.click("Confirm Unknown")
        self.assertNotIn("ACC-004", adapter.get_algorithm(first)["answers"])
        details = next(item for item in self.app.text_area if item.label == "Why is this unknown?")
        details.set_value("The supplier has yet to provide the architecture.")
        self.click("Confirm Unknown")
        self.assertEqual(adapter.get_algorithm(first)["answers"]["ACC-004"]["value"], ["Unknown"])
        self.assertIn("ACC-002", self.state.d23_conversations[first]["skipped"])
        self.assertTrue(any("D2.3 has unresolved" in item.value for item in self.app.markdown))
        revision = self.state.d23_answer_revision
        draft = f"d23-answer-{first}-ACC-005-{revision}-details"
        self.app.text_area(key=draft).set_value("Draft supplier note").run()
        self.click("Add another algorithm")
        self.submit("ux_d23_proposal-message", "Another model v3")
        self.assertEqual(adapter.algorithm_ids, (first,))
        self.click("Confirm algorithm record")
        second = adapter.algorithm_ids[-1]
        self.assertNotEqual(first, second)
        self.assertNotIn("ACC-004", adapter.get_algorithm(second)["answers"])
        self.app.text_input(key=f"d23-answer-{second}-ACC-002-{revision}").set_value("AIF-004")
        self.click("Confirm D2.3 answer")
        self.click("Resume Retina Reader — 2.5")
        self.assertEqual(self.state.d23_active_algorithm_id, first)
        revision = self.state.d23_answer_revision
        self.assertEqual(self.app.text_area(key=f"d23-answer-{first}-ACC-005-{revision}-details").value,
                         "Draft supplier note")

    def test_dataset_conversation_creates_only_on_confirmation_and_gates_followups(self):
        self.click("Continue with gaps")
        self.assertTrue(any("What dataset would you like to start with?" in item.value for item in self.app.markdown))
        adapter = self.state.d24_adapter
        self.submit("ux_d24_proposal_dataset-message", "The dataset is called Evaluation cohort 2025")
        self.assertEqual(adapter.record_ids("dataset"), ())
        self.assertTrue(any(item.label == "Manage records and answers" for item in self.app.expander))
        self.click("Confirm new record")
        first = adapter.record_ids("dataset")[0]
        self.assertEqual(adapter.get_answers(first), {"DEP-001.dataset_name_version": "Evaluation cohort 2025"})
        self.assertEqual(len(self.app.chat_input), 1)
        self.assertNotIn("DEP-001.role_other", adapter.active_fields(first))
        role = self.app.multiselect(key=f"d24-answer-{first}-DEP-001.role-0")
        role.set_value(["Other"])
        self.click("Confirm D2.4 answer")
        self.assertIn("DEP-001.role_other", adapter.active_fields(first))
        self.assertTrue(any("other option" in item.value.casefold() for item in self.app.markdown))
        self.click("Skip for now")
        self.assertNotIn("DEP-001.role_other", adapter.get_answers(first))
        self.assertIn("DEP-001.role_other", self.state.d24_conversations[first]["skipped"])
        self.assertTrue(any("deferred questions" in item.value for item in self.app.caption))
        draft = f"d24-answer-{first}-DEP-001.source_documentation-2"
        self.app.text_area(key=draft).set_value("Draft inventory reference").run()
        self.click("Describe another dataset")
        self.submit("ux_d24_proposal_dataset-message", "External test cohort")
        self.assertEqual(adapter.record_ids("dataset"), (first,))
        self.click("Confirm new record")
        second = adapter.record_ids("dataset")[-1]
        self.assertEqual(adapter.get_answers(second), {"DEP-001.dataset_name_version": "External test cohort"})
        self.click("Resume Evaluation cohort 2025")
        self.assertEqual(adapter.selected_record_id, first)
        self.assertEqual(adapter.get_answers(first)["DEP-001.role"], ["Other"])
        self.assertEqual(self.app.text_area(key=draft).value, "Draft inventory reference")

    def test_d24_guided_scope_navigation_and_unknown_are_explicit(self):
        self.click("Continue with gaps")
        self.click("Continue to ai function / version with gaps")
        self.assertEqual(self.state.d24_active_scope, "function")
        self.assertTrue(any("would you like to document?" in item.value for item in self.app.markdown))
        self.click("Continue to supporting document with gaps")
        self.assertEqual(self.state.d24_active_scope, "document")
        self.click("Continue to profile-wide gmlp with gaps")
        adapter = self.state.d24_adapter
        self.assertEqual(adapter.selected_record_id, adapter.GMLP)
        self.click("I don't know")
        self.assertEqual(adapter.get_answers(adapter.GMLP), {})
        self.click("Confirm Unknown")
        self.assertEqual(adapter.get_answers(adapter.GMLP), {"DEP-036-trigger": "Unknown"})
        self.assertNotIn("DEP-036", adapter.active_fields(adapter.GMLP))
        self.assertTrue(any("D2.4 has unresolved" in item.value for item in self.app.markdown))
