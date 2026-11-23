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
        if label == "Continue with gaps":
            self.click("Confirm continue with gaps")

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
            if field == "ACC-009":
                value = ["None"]
            adapter.save_answer(algorithm_id, field, value, details="Confirmed explanation", evidence="Document §1")

    def test_sidebar_lists_all_sections_and_counts_applicable_responses(self):
        self.fill_bridge("D2.1")
        bridge = self.state.questionnaire_bridge
        conditional = bridge.get_active_conditional_fields("D2.1")
        adapter = D23AnswerAdapter()
        algorithm = adapter.add_algorithm("Screening model")
        adapter.save_answer(algorithm, "ACC-001", "Screening model")
        self.state.d23_adapter = adapter
        datasets = D24AnswerAdapter()
        datasets.create_record("dataset")
        self.state.d24_adapter = datasets
        self.app.run()
        rows = [item.value for item in self.app.sidebar.markdown]
        self.assertEqual(len(rows), 5)
        self.assertTrue(any(f"{24 + len(conditional)}/{24 + len(conditional)} recorded" in row for row in rows))
        self.assertTrue(any("D2.3" in row and "1/" in row and "gaps to review" in row for row in rows))
        self.assertTrue(any("D2.4" in row and "1 record" in row and "gaps" in row for row in rows))
        self.assertTrue(any("D2.5" in row and "Unavailable" in row for row in rows))

    def test_documented_unknown_is_a_gap_without_reasking(self):
        adapter = D23AnswerAdapter()
        algorithm = adapter.add_algorithm("Screening model")
        self.fill_algorithm(adapter, algorithm)
        adapter.save_answer(algorithm, "ACC-021", "Unknown", details="The procedure record is unavailable.")
        self.assertFalse(adapter.build_record(algorithm)["validation_problems"])
        self.state.d23_adapter = adapter
        self.state.d23_mode = True
        self.state.d23_active_algorithm_id = algorithm
        self.state.d23_answer_revision = 0
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Supporting information remains unresolved" in item.value for item in self.app.markdown))
        self.assertTrue(any("required responses are recorded" in item.value for item in self.app.markdown))
        self.assertFalse(any(item.label == "Continue to D2.4" for item in self.app.button))
        self.assertFalse(any(item.label == "Skip for now" for item in self.app.button))

    def test_automatic_d22_and_completed_footer_then_record_entry(self):
        self.fill_bridge("D2.1")
        self.state.intake_started = True
        self.state.needs_next_question = True
        self.app.run()
        self.assertEqual(self.state.active_questionnaire, "D2.2")
        self.assertTrue(self.state.asked_field.startswith("AIF-"))
        self.fill_bridge("D2.2")
        self.state.unified_messages.append({"role": "user", "content": "Previously documented AI functions."})
        self.state.needs_next_question = True
        self.app.run()
        self.assertTrue(self.state.questionnaire_complete)
        self.assertTrue(self.state.d23_mode)
        self.assertTrue(any(item.value == "Previously documented AI functions." for item in self.app.markdown))
        self.app.run()
        self.assertEqual(sum("Let’s document the algorithms" in item.value for item in self.app.markdown), 1)
        self.click("Back to D2.1 and D2.2")
        self.assertFalse(self.state.d23_mode)
        self.assert_footer("D2.1 and D2.2 complete", "Continue to D2.3", self.app.chat_input[0])
        self.click("Continue to D2.3")
        self.assertTrue(any("What is its name and version?" in item.value for item in self.app.markdown))
        self.assertFalse(any("D2.3 has unresolved" in item.value for item in self.app.markdown))
        self.assertFalse(any(item.label == "Review remaining gaps" for item in self.app.expander))
        panel = next(item for item in self.app.expander if item.label == "Review & Edit")
        self.assertFalse(panel.proto.expanded)
        for label in ("Add algorithm", "Continue with gaps", "Restore from JSON"):
            self.assertTrue(any(getattr(item, "label", None) == label for item in panel))
        self.button("Continue with gaps").click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.state.d23_mode)
        gaps = next(item for item in self.app.expander if item.label == "Review remaining gaps")
        self.assertTrue(gaps.proto.expanded)
        self.click("Confirm continue with gaps")
        self.assertTrue(any("What dataset would you like to start with?" in item.value for item in self.app.markdown))

    def test_completed_algorithm_can_move_to_datasets_in_chat(self):
        adapter = D23AnswerAdapter()
        algorithm = adapter.add_algorithm("Screening model")
        self.fill_algorithm(adapter, algorithm)
        adapter.save_answer(algorithm, "ACC-021", "Unknown", details="Waiting for the procedure record.")
        self.state.d23_adapter = adapter
        self.state.d23_mode = True
        self.state.d23_answer_revision = 0
        self.state.d23_active_algorithm_id = algorithm
        self.app.run()
        self.assertTrue(any("Some documentation gaps remain" in node.value for node in self.app.markdown))
        self.assertTrue(any("Do you need to document another algorithm?" in item.value for item in self.app.markdown))
        self.app.chat_input(key=f"d23-chat-input-{algorithm}").set_value("Yes.").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any(item.value == "Yes." for item in self.app.text))
        self.assertEqual(adapter.algorithm_ids, (algorithm,))
        self.assertIsNotNone(self.app.chat_input(key="ux_d23_proposal-message"))
        self.click("Return to current algorithm")
        self.app.chat_input(key=f"d23-chat-input-{algorithm}").set_value("No.").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.state.d24_mode)
        self.assertTrue(any(item.value == "No." for item in self.app.text))

    def test_dataset_boundary_accepts_chat_navigation_and_keeps_previous_turns(self):
        adapter = D24AnswerAdapter()
        record = adapter.create_record("dataset")
        adapter.save_answer(record, "DEP-001.dataset_name_version", "Validation cohort")
        self.state.d24_adapter = adapter
        self.state.d23_mode = True
        self.state.d24_mode = True
        self.state.d24_conversations = {
            record: {"turns": ["Previous dataset detail."], "pending": {}, "notice": "",
                     "skipped": set(adapter.active_fields(record))},
        }
        self.app.run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("Do you need to document another dataset?" in node.value for node in self.app.markdown))
        self.app.chat_input(key=f"d24-message-{record}").set_value("No.").run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.state.d24_active_scope, "function")
        self.assertTrue(any(node.value == "Previous dataset detail." for node in self.app.text))
        self.assertTrue(any(node.value.startswith("Do you need to document another dataset?") for node in self.app.text))

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
        panel = next(item for item in self.app.expander if item.label == "Review & Edit")
        self.assertTrue(any(getattr(item, "label", None) == "Continue to D2.4" for item in panel))
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
