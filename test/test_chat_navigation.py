from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.d23_adapter import D23AnswerAdapter
from app.chatbot.d24_adapter import D24AnswerAdapter
from app.chatbot.questionnaire_bridge import QUESTIONNAIRE_FIELDS
from app.deliverable_2.questionnaires.algorithm_change_control import FIELDS, FRAMEWORKS


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"


class ChatNavigationTests(unittest.TestCase):
    def setUp(self):
        gemini = self.enterContext(patch.object(
            chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")
        ))
        self.addCleanup(gemini.assert_not_called)
        self.app = AppTest.from_file(str(CHAT_APP), default_timeout=40).run()
        self.state = self.app.session_state

    def button(self, label):
        return next(item for item in self.app.button if item.label == label)

    def click(self, label):
        self.button(label).click().run()
        self.assertFalse(self.app.exception)

    def assert_footer(self, phrase, button_label, after):
        nodes = list(self.app._tree)
        message = next(item for item in self.app.markdown if phrase in item.value)
        status_index = next(i for i, node in enumerate(nodes) if getattr(node, "proto", None) is message.proto)
        button_index = next(i for i, node in enumerate(nodes) if getattr(node, "proto", None) is self.button(button_label).proto)
        before_index = next(i for i, node in enumerate(nodes) if getattr(node, "proto", None) is after.proto)
        self.assertLess(before_index, status_index)
        self.assertLess(status_index, button_index)

    def fill_bridge(self, section):
        bridge = self.state.questionnaire_bridge
        for field in QUESTIONNAIRE_FIELDS[section]:
            options = bridge.get_field_options(field)
            value = options[0] if options else "Confirmed example"
            if bridge.get_field_type(field) == "multiselect":
                value = [value]
            self.assertTrue(bridge.save_answer(field, value)[0], field)
        for field in bridge.get_active_conditional_fields(section):
            self.assertTrue(bridge.save_answer(field, "Confirmed follow-up")[0], field)

    def fill_algorithm(self, adapter, algorithm_id):
        for definition in FIELDS:
            field = definition["id"]
            if field not in adapter.active_field_ids(algorithm_id):
                continue
            kind, options = definition["type"], definition["options"]
            if kind == "perframework":
                value = {framework: options[0] for framework in FRAMEWORKS}
            elif kind == "multiselect":
                value = [options[0]]
            elif kind == "select":
                value = options[0]
            else:
                value = "AIF-001" if field == "ACC-002" else "Confirmed example"
            adapter.save_answer(algorithm_id, field, value, details="Confirmed explanation", evidence="Document §1")

    def test_automatic_d22_and_completed_footer_then_record_entry(self):
        self.fill_bridge("D2.1")
        self.state.intake_started = True
        self.state.needs_next_question = True
        self.app.run()
        self.assertEqual(self.state.active_questionnaire, "D2.2")
        self.assertTrue(self.state.asked_field.startswith("AIF-"))
        self.fill_bridge("D2.2")
        self.state.needs_next_question = True
        self.app.run()
        self.assertTrue(self.state.questionnaire_complete)
        self.assert_footer("D2.1 and D2.2 complete", "Continue to D2.3", self.app.chat_input[0])
        self.app.run()
        self.assertEqual(sum("D2.1 and D2.2 complete" in item.value for item in self.app.markdown), 1)
        self.click("Continue to D2.3")
        self.assertTrue(any("Which algorithm are you describing?" in item.value for item in self.app.markdown))
        self.assert_footer("D2.3 has unresolved", "Continue with gaps", self.button("Add algorithm"))
        self.click("Continue with gaps")
        self.assertTrue(any("Add a dataset to begin" in item.value for item in self.app.caption))

    def test_algorithm_completion_is_section_wide_and_stale_navigation_is_ignored(self):
        adapter = D23AnswerAdapter()
        first, second = adapter.add_algorithm("First"), adapter.add_algorithm("Second")
        self.fill_algorithm(adapter, first)
        self.assertFalse(adapter.build_record(first)["validation_problems"])
        self.state.d23_adapter = adapter
        self.state.d23_mode = True
        self.state.d23_answer_revision = 0
        self.state.d23_active_algorithm_id = first
        self.app.run()
        self.assertNotIn("Continue to D2.4", [item.label for item in self.app.button])
        self.click("Resume unanswered questions")
        self.assertEqual(self.state.d23_active_algorithm_id, second)
        self.fill_algorithm(adapter, second)
        self.app.run()
        self.assert_footer("D2.3 complete", "Continue to D2.4", self.app.chat_input[0])
        stale = self.button("Continue to D2.4")
        stale.click()
        self.click("Back to D2.1 and D2.2")
        self.assertFalse(self.state.d24_mode)
        self.assertFalse(self.state.d23_mode)
        self.assertEqual(adapter.algorithm_ids, (first, second))

    def test_cross_section_navigation_keeps_pending_review_and_edited_draft(self):
        self.state.questionnaire_bridge.save_answer("PIP-001", "Confirmed product")
        self.state.field_suggestions = {"PIP-002": "Suggested use"}
        self.state.unified_messages.append({"role": "user", "content": "A retained turn"})
        self.app.run()
        self.app.text_area(key="review_PIP-002_0").set_value("Edited review draft").run()
        self.click("Continue with gaps")
        self.click("Back to D2.1 and D2.2")
        self.assertEqual(self.state.field_suggestions, {"PIP-002": "Suggested use"})
        self.assertEqual(self.app.text_area(key="review_PIP-002_0").value, "Edited review draft")
        self.assertEqual(self.state.questionnaire_bridge.get_product_profile(), {"PIP-001": "Confirmed product"})
        self.assertTrue(any(item.value == "A retained turn" for item in self.app.markdown))

    def test_d24_required_gaps_optional_controls_unknown_and_gmlp_resume(self):
        adapter = D24AnswerAdapter()
        dataset = adapter.create_record("dataset")
        evaluation = adapter.create_record("function")
        document = adapter.create_record("document")
        for record_id in (dataset, evaluation, document):
            for field in adapter.field_ids(record_id):
                active = adapter.active_fields(record_id)
                if field not in active or field == "DEP-012-trigger":
                    continue
                info = active[field]
                value = "Confirmed example" if info.kind == "text" else info.options[0]
                if info.kind == "multiselect":
                    value = [value]
                if field == "DEP-003":
                    value = "Unknown"
                adapter.save_answer(record_id, field, value)
        adapter.save_answer(adapter.GMLP, "DEP-036-trigger", "Yes")
        self.state.d24_adapter = adapter
        self.state.d23_mode = True
        self.state.d24_mode = True
        self.app.run()
        self.assertTrue(any("D2.4 has unresolved" in item.value for item in self.app.markdown))
        self.click("Resume unanswered questions")
        self.assertEqual(adapter.selected_record_id, adapter.GMLP)
        adapter.save_answer(adapter.GMLP, "DEP-036", "Yes")
        adapter.save_answer(adapter.GMLP, "DEP-036-document", "Document §4")
        self.app.run()
        self.assertTrue(any("D2.4 complete" in item.value for item in self.app.markdown))
        self.assertNotIn("DEP-012-trigger", adapter.get_answers(dataset))
        self.assertEqual(adapter.get_answers(dataset)["DEP-003"], "Unknown")
