import json
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.chat_navigation import propose_record_identity
from app.deliverable_2.questionnaires.algorithm_change_control import LOCKED


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"
RETINAGUARD = (
    "Our algorithm is called RetinaGuard DR Detection Algorithm, version 1.0. "
    "It uses a convolutional neural network to analyze retinal fundus photographs and detect signs of diabetic retinopathy. "
    "The algorithm generates a risk score that ophthalmologists review to support clinical decision-making."
)


class IdentityProposalTests(unittest.TestCase):
    def test_structured_ambiguous_and_missing_versions(self):
        self.assertEqual(propose_record_identity(RETINAGUARD, algorithm=True),
                         ("RetinaGuard DR Detection Algorithm", "1.0"))
        self.assertEqual(propose_record_identity("Our model is RetinaGuard, version 1.0 or 2.0.", algorithm=True),
                         ("RetinaGuard", ""))
        self.assertEqual(propose_record_identity("RetinaGuard. It produces an alert.", algorithm=True),
                         ("RetinaGuard", ""))
        self.assertEqual(propose_record_identity("We use a CNN that produces an alert.", algorithm=True), ("", ""))
        self.assertEqual(propose_record_identity("RetinaGuard uses a CNN.", algorithm=True), ("", ""))
        self.assertEqual(propose_record_identity("Our algorithm is a classifier for retinal images.", algorithm=True),
                         ("", ""))
        self.assertEqual(propose_record_identity("RetinaGuard (version 1.0). It produces an alert.", algorithm=True),
                         ("RetinaGuard", "1.0"))
        self.assertEqual(propose_record_identity("The report is called Validation report, version 2.", include_version=False),
                         ("Validation report", ""))


class GuidedConversationTests(unittest.TestCase):
    def setUp(self):
        gemini = self.enterContext(patch.object(
            chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")
        ))
        self.addCleanup(gemini.assert_not_called)
        self.d23_extractor = self.enterContext(patch("app.chatbot.d23_chat.extract_d23_candidates", return_value=({}, "")))
        self.d24_extractor = self.enterContext(patch("app.chatbot.d24_chat.extract_d24_candidates", return_value=({}, "")))
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

    def mock_proposals(self, section, candidates):
        extractor = self.d23_extractor if section == "D2.3" else self.d24_extractor
        extractor.side_effect = (chat_llm.extract_d23_candidates if section == "D2.3"
                                 else chat_llm.extract_d24_candidates)
        calls = []

        def respond(prompt, *_args, **_kwargs):
            payload = json.loads("{" + prompt.rsplit("\n{", 1)[1])
            calls.append(payload)
            keys = ("algorithm_id", "source_id") if section == "D2.3" else ("record_id", "scope", "source_id")
            return {**{key: payload[key] for key in keys}, "candidates": candidates}

        self.enterContext(patch.object(chat_llm, "_request_extraction", side_effect=respond))
        return calls

    def test_exact_retinaguard_description_becomes_a_single_review_turn(self):
        proposed = {
            "ACC-004": {"value": ["CNN"], "quote": "It uses a convolutional neural network"},
            "AIF-006": {"value": ["Risk score"], "quote": "generates a risk score"},
        }
        calls = self.mock_proposals("D2.3", proposed)
        adapter = self.state.d23_adapter
        self.submit("ux_d23_proposal-message", RETINAGUARD)
        self.assertEqual(adapter.algorithm_ids, ())
        self.assertEqual(calls, [])
        names = {item.label: item.value for item in self.app.text_input}
        self.assertEqual(names["Record name"], "RetinaGuard DR Detection Algorithm")
        self.assertEqual(names["Record version"], "1.0")
        self.click("Confirm algorithm record")
        first = adapter.algorithm_ids[0]
        snapshot = adapter.get_algorithm(first)
        self.assertEqual(snapshot["name"], "RetinaGuard DR Detection Algorithm")
        self.assertEqual(snapshot["version"], "1.0")
        self.assertEqual(set(snapshot["answers"]), {"ACC-001"})
        self.assertEqual(calls[0]["algorithm_id"], first)
        self.assertEqual(calls[0]["source_id"], "1")
        self.assertEqual(calls[0]["user_message"], RETINAGUARD)
        conversation = self.state.d23_conversations[first]
        self.assertEqual(conversation["turns"], [RETINAGUARD])
        self.assertEqual(set(conversation["candidates"]), {"ACC-004"})
        self.assertEqual(conversation["candidates"]["ACC-004"]["source_id"], "1")
        self.assertEqual(sum(item.value == RETINAGUARD for item in self.app.text), 1)
        self.app.run()
        self.assertEqual(len(calls), 1)
        self.click("Add another algorithm")
        proposed.clear()
        proposed.update({
            "ACC-004": {"value": ["CNN"], "quote": "It uses a convolutional neural network"},
            "ACC-008": {"value": LOCKED, "quote": "It is locked after release"},
        })
        second_message = "The algorithm is called Separate Model. It uses a convolutional neural network. It is locked after release."
        self.submit("ux_d23_proposal-message", second_message)
        self.assertEqual(len(calls), 1)
        self.click("Confirm algorithm record")
        second = adapter.algorithm_ids[-1]
        self.assertNotEqual(first, second)
        self.assertEqual(adapter.get_algorithm(second)["version"], "")
        self.assertEqual(set(adapter.get_algorithm(second)["answers"]), {"ACC-001"})
        self.assertEqual(set(self.state.d23_conversations[second]["candidates"]), {"ACC-004", "ACC-008"})
        self.assertEqual(self.state.d23_conversations[first]["turns"], [RETINAGUARD])
        self.assertEqual(calls[-1]["algorithm_id"], second)
        self.assertEqual(calls[-1]["user_message"], second_message)
        self.assertEqual(len(calls), 2)
        self.app.button(key=f"d23-review-{second}-1-ACC-008-confirm").click().run()
        self.assertEqual(adapter.get_algorithm(second)["answers"]["ACC-008"]["value"], LOCKED)
        self.assertNotIn("ACC-008", adapter.get_algorithm(first)["answers"])
        self.assertEqual(len(calls), 2)

    def test_d24_initial_descriptions_stay_with_their_confirmed_scope(self):
        self.click("Continue with gaps")
        proposed = {}
        calls = self.mock_proposals("D2.4", proposed)
        cases = (
            ("dataset", "The dataset is called External Cohort, version 2. It contains 500 scans. Collection was Retrospective.",
             "External Cohort, version 2", "DEP-001.dataset_name_version", {
                 "DEP-005": {"value": "500 scans", "quote": "500 scans"},
                 "DEP-003": {"value": "Retrospective", "quote": "Collection was Retrospective."},
             }),
            ("function", "The evaluation is called Benchmark, version 3. The metric was Accuracy.",
             "Benchmark, version 3", "DEP-019-versions", {
                 "DEP-020-metrics": {"value": ["Accuracy"], "quote": "The metric was Accuracy."},
             }),
            ("document", "The document is titled Validation report, version 2. The document ID is Evidence-17.",
             "Validation report", "title", {
                 "version": {"value": "2", "quote": "version 2"},
                 "document_id": {"value": "Evidence-17", "quote": "Evidence-17"},
             }),
        )
        adapter = self.state.d24_adapter
        for index, (scope, description, identity, field, candidates) in enumerate(cases):
            self.app.radio(key="d24-section").set_value(scope).run()
            proposed.clear()
            proposed.update(candidates)
            self.submit(f"ux_d24_proposal_{scope}-message", description)
            self.assertEqual(adapter.record_ids(scope), ())
            self.assertEqual(len(calls), index)
            self.assertEqual(next(item.value for item in self.app.text_input if item.label == "Record name"), identity)
            self.assertNotIn("Record version", [item.label for item in self.app.text_input])
            self.click("Confirm new record")
            record = adapter.record_ids(scope)[0]
            self.assertEqual(adapter.get_answers(record), {field: identity})
            self.assertEqual(self.state.d24_conversations[record]["turns"], [description])
            self.assertEqual(set(self.state.d24_conversations[record]["pending"]), set(candidates))
            self.assertEqual(calls[-1]["record_id"], record)
            self.assertEqual(calls[-1]["scope"], scope)
            self.assertEqual(calls[-1]["source_id"], "1")
            self.assertEqual(calls[-1]["user_message"], description)
            self.assertEqual(sum(item.value == description for item in self.app.text), 1)
            self.app.run()
            self.assertEqual(len(calls), index + 1)

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
