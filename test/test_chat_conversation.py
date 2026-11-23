import json
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.chat_navigation import propose_record_identity
from app.deliverable_2.questionnaires.algorithm_change_control import BY_ID, LOCKED


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"
RETINAGUARD = (
    "Our algorithm is called RetinaGuard DR Detection Algorithm, version 1.0. "
    "It uses a convolutional neural network to analyze retinal fundus photographs and detect signs of diabetic retinopathy. "
    "The algorithm generates a risk score that ophthalmologists review to support clinical decision-making."
)

FUNCTION_DESCRIPTION = (
    "The RetinaGuard DR Detection Algorithm implements the diabetic retinopathy detection and screening function described in D2.2. "
    "It analyzes retinal fundus photographs using a convolutional neural network (CNN) and generates a risk score to support ophthalmologists in clinical decision-making."
)
COMPONENT_DESCRIPTION = (
    "Yes. The RetinaGuard DR Detection Algorithm uses open-source software components, including TensorFlow and Keras, "
    "to develop and train its convolutional neural network (CNN). These libraries support model development and training, "
    "while the algorithm itself was developed in-house. No third-party pre-trained models are incorporated. "
    "The specific library versions have not yet been confirmed."
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
        if label == "Continue with gaps":
            self.click("Confirm continue with gaps")

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

    def test_confirmed_d22_context_and_reference_feedback(self):
        evidence = "Analyzes retinal fundus photographs to detect diabetic retinopathy."
        self.assertTrue(self.state.questionnaire_bridge.save_answer("AIF-004", evidence)[0])
        proposed = {}
        calls = self.mock_proposals("D2.3", proposed)
        self.submit("ux_d23_proposal-message", RETINAGUARD)
        self.click("Confirm algorithm record")
        adapter = self.state.d23_adapter
        record = adapter.algorithm_ids[0]
        key = f"d23-chat-input-{record}"
        proposed["ACC-002"] = {"value": "Retinal screening", "quote": FUNCTION_DESCRIPTION}
        self.submit(key, FUNCTION_DESCRIPTION)
        self.assertTrue(any("couldn't identify a supported answer" in node.value for node in self.app.markdown))
        self.assertTrue(any("Which confirmed AI-function entries" in node.value for node in self.app.markdown))
        self.assertFalse(any(node.value == "Which of the AI functions from Deliverable 2.2 does this algorithm implement?"
                             for node in self.app.markdown))
        proposed["ACC-002"].update(value="AIF-006", reference_evidence={"AIF-006": evidence})
        self.submit(key, FUNCTION_DESCRIPTION)
        self.assertNotIn("ACC-002", self.state.d23_conversations[record]["candidates"])
        proposed["ACC-002"].update(value="AIF-004", reference_evidence={"AIF-004": evidence})
        self.submit(key, FUNCTION_DESCRIPTION)
        self.assertEqual(calls[-1]["confirmed_d22_answers"], {"AIF-004": evidence})
        self.assertTrue(any(node.value.startswith("AIF-004 ·") for node in self.app.caption))
        self.assertTrue(any(node.value == evidence for node in self.app.text))
        self.assertEqual(calls[-1]["user_message"], FUNCTION_DESCRIPTION)
        self.assertNotIn("ACC-002", adapter.get_algorithm(record)["answers"])
        self.assertTrue(any("Review the extracted information" in node.value for node in self.app.info))
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-002"]["value"], "AIF-004")
        self.assertEqual(self.state.d23_conversations[record]["turns"][-1], FUNCTION_DESCRIPTION)
        self.assertFalse(any(node.label == "Confirm suggestion" for node in self.app.button))
        self.assertTrue(any("learning approach" in node.value.lower() for node in self.app.markdown))

    def start_algorithm_at(self, target):
        self.submit("ux_d23_proposal-message", RETINAGUARD)
        self.click("Confirm algorithm record")
        adapter = self.state.d23_adapter
        record = adapter.algorithm_ids[0]
        for field in adapter.active_field_ids(record):
            if field == target:
                break
            if field in adapter.get_algorithm(record)["answers"]:
                continue
            definition = BY_ID[field]
            options = definition["options"]
            value = options[0] if options else "AIF-004"
            if definition["type"] == "multiselect":
                value = [value]
            adapter.save_answer(record, field, value, details="Confirmed example")
        self.app.run()
        return adapter, record

    def test_reproducibility_keeps_optional_explanation_with_yes(self):
        explanation = ("The algorithm uses fixed parameters during inference and is expected to produce "
                       "consistent risk scores when processing identical images under identical operating conditions.")
        proposed = {}
        self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-006")
        proposed["ACC-006"] = {"value": "Yes", "quote": "Yes", "details": explanation}
        self.submit(f"d23-chat-input-{record}", f"Yes. {explanation}")
        key = f"d23-review-{record}-2-ACC-006"
        self.assertEqual(self.app.text_area(key=f"{key}-details").value, explanation)
        self.assertNotIn("ACC-006", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-006"]["details"], explanation)
        self.assertTrue(any("changeable after release" in node.value for node in self.app.markdown))

    def test_retraining_reply_survives_empty_extractor_output(self):
        explanation = (
            "Clinician corrections, site data, and clinical outcomes are collected and securely stored. "
            "The data undergo privacy review, quality checks, and clinical validation before approved use in retraining. "
            "Updated models require validation and manufacturer approval before release."
        )
        self.mock_proposals("D2.3", {})
        adapter, record = self.start_algorithm_at("ACC-012")
        self.submit(f"d23-chat-input-{record}", f"Yes. {explanation}")
        key = f"d23-review-{record}-2-ACC-012"
        self.assertEqual(self.app.selectbox(key=key).value, "Yes")
        self.assertEqual(self.app.text_area(key=f"{key}-details").value, explanation)
        self.assertNotIn("ACC-012", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-012"]["details"], explanation)
        self.assertTrue(any("planned or anticipated" in node.value for node in self.app.markdown))

    def test_followup_preserves_pending_no_and_advances_after_confirmation(self):
        proposed = {}
        calls = self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-006")
        self.submit(f"d23-chat-input-{record}", "No.")
        self.assertTrue(any("source of variability" in node.value for node in self.app.markdown))
        self.assertNotIn("ACC-006", adapter.get_algorithm(record)["answers"])
        self.assertFalse(self.app.chat_input(key=f"d23-chat-input-{record}").disabled)
        detail = "Randomized preprocessing changes the score for otherwise identical inputs."
        proposed["ACC-006"] = {"value": "No", "quote": detail, "details": detail}
        self.submit(f"d23-chat-input-{record}", detail)
        self.assertEqual(calls[-1]["pending_answer_followup"]["quote"], "No")
        self.assertEqual(calls[-1]["user_message"], detail)
        suggestion = self.state.d23_conversations[record]["candidates"]["ACC-006"]
        self.assertEqual((suggestion["quote"], suggestion["source_id"], suggestion["detail_source_id"]),
                         ("No", "2", "3"))
        self.assertEqual(self.app.text_area(key=f"d23-review-{record}-3-ACC-006-details").value, detail)
        self.assertNotIn("ACC-006", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        answer = adapter.get_algorithm(record)["answers"]["ACC-006"]
        self.assertEqual((answer["value"], answer["details"], answer["evidence"]), ("No", detail, ""))
        self.assertTrue(any("changeable after release" in node.value for node in self.app.markdown))
        self.assertEqual(len(calls), 3)

    def test_partial_retraining_explanation_combines_with_focused_followup(self):
        proposed = {}
        calls = self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-012")
        data_path = "Clinician corrections are stored in a restricted retraining queue."
        screening = "A clinical reviewer screens each correction before approval."
        question = "Who screens the corrections before retraining?"
        proposed["ACC-012"] = {
            "value": "Yes", "quote": "Yes", "details": data_path, "missing_detail": question,
        }
        key = f"d23-chat-input-{record}"
        self.submit(key, f"Yes. {data_path}")
        self.assertTrue(any(node.value == question for node in self.app.markdown))
        self.assertEqual(self.app.text_area(key=f"d23-review-{record}-2-ACC-012-details").value, data_path)
        proposed["ACC-012"] = {"value": "Yes", "quote": screening, "details": screening}
        self.submit(key, screening)
        self.assertEqual(calls[-1]["pending_answer_followup"]["details"], data_path)
        self.assertEqual(calls[-1]["original_reply"], f"Yes. {data_path}")
        self.assertEqual(self.app.text_area(key=f"d23-review-{record}-3-ACC-012-details").value,
                         f"{data_path} {screening}")
        self.assertTrue(any(node.value == question for node in self.app.text))
        self.assertFalse(any(node.value == question for node in self.app.markdown))
        self.assertNotIn("ACC-012", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-012"]["details"],
                         f"{data_path} {screening}")

    def test_controlled_manufacturer_release_overrides_bare_fixed_selection(self):
        proposed = {}
        self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-007")
        response = ("These settings are fixed after release. Any changes require manufacturer "
                    "approval, validation, and a controlled software release.")
        proposed["ACC-007"] = {"value": "Fixed", "quote": "These settings are fixed after release."}
        self.submit(f"d23-chat-input-{record}", response)
        key = f"d23-review-{record}-2-ACC-007"
        self.assertEqual(self.app.selectbox(key=key).value, "Changed only by manufacturer release")
        self.assertEqual(self.app.text_area(key=f"{key}-details").value, response)
        self.assertNotIn("ACC-007", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-007"]["details"], response)

    def test_multiselect_preserves_verified_excerpts(self):
        proposed = {}
        self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-003")
        quote = "The algorithm uses supervised learning and fine-tunes a pre-trained model."
        details = "Training uses labeled examples reviewed by two specialists."
        proposed["ACC-003"] = {
            "value": ["supervised", "Fine-tuned pre-trained/foundation model"], "quote": quote,
            "explanation": [details, "Invented details"],
        }
        self.submit(f"d23-chat-input-{record}", f"{quote} {details}")
        key = f"d23-review-{record}-2-ACC-003"
        self.assertEqual(self.app.text_area(key=f"{key}-details").value, details)
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-003"]["value"],
                         ["Supervised", "Fine-tuned pre-trained/foundation model"])

    def open_framework_status_question(self):
        adapter, record = self.start_algorithm_at("ACC-013")
        adapter.save_answer(record, "ACC-013", "Yes")
        for field in adapter.active_field_ids(record):
            if field == "ACC-020":
                break
            if field in adapter.get_algorithm(record)["answers"]:
                continue
            definition = BY_ID[field]
            options = definition["options"]
            value = options[0] if options else "Verified change plan"
            if definition["type"] == "multiselect":
                value = [value]
            adapter.save_answer(record, field, value, details="Confirmed details")
        self.app.run()
        return adapter, record

    def test_framework_statuses_survive_malformed_model_statuses_and_followup(self):
        proposed = {}
        self.mock_proposals("D2.3", proposed)
        adapter, record = self.open_framework_status_question()
        self.assertTrue(any("Medical Device Regulation" in node.value for node in self.app.markdown))
        response = ("Health Canada: PCCP under development, not submitted or authorized. "
                    "FDA: PCCP under development, not submitted or authorized. EU MDR: "
                    "Change-control documentation under development; conformity assessment pending.")
        proposed["ACC-020"] = {
            "value": {"HC": "Draft", "U.S. FDA": "Draft", "EU MDR": "Pending conformity assessment"},
            "quote": response,
        }
        self.submit(f"d23-chat-input-{record}", response)
        key = f"d23-review-{record}-2-ACC-020"
        self.assertEqual(self.app.selectbox(key=f"{key}-Health Canada").value, "Not submitted")
        self.assertEqual(self.app.selectbox(key=f"{key}-FDA").value, "Not submitted")
        self.assertIsNone(self.app.selectbox(key=f"{key}-EU MDR").value)
        self.assertIsNone(self.app.selectbox(key=f"{key}-EU AI Act").value)
        self.assertTrue(any("status applies to the change plan for EU MDR" in node.value for node in self.app.markdown))
        self.assertNotIn("ACC-020", adapter.get_algorithm(record)["answers"])
        proposed.clear()
        self.submit(f"d23-chat-input-{record}", "EU MDR: not submitted.")
        self.click("Confirm suggestion")
        result = adapter.get_algorithm(record)["answers"]["ACC-020"]
        self.assertEqual(result["value"]["EU MDR"], "Not submitted")
        self.assertIsNone(result["value"]["EU AI Act"])
        self.assertTrue(any(node.value == "What is the change-plan status for EU AI Act?"
                            for node in self.app.markdown))
        self.submit(f"d23-chat-input-{record}", "EU AI Act: planned for submission.")
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-020"]["value"], {
            "Health Canada": "Not submitted", "FDA": "Not submitted",
            "EU MDR": "Not submitted", "EU AI Act": "Planned for submission",
        })

    def test_framework_filing_receipt_does_not_become_authorization(self):
        self.mock_proposals("D2.3", {})
        _, record = self.open_framework_status_question()
        self.submit(f"d23-chat-input-{record}", "U.S. FDA: submission accepted for review.")
        self.assertFalse(self.state.d23_conversations[record]["candidates"])
        self.assertTrue(any("Available statuses:" in node.value for node in self.app.caption))
        self.click("Edit this answer manually")
        tools = next(node for node in self.app.expander if node.label == "Manage algorithms and answers")
        self.assertTrue(tools.proto.expanded)

    def test_affected_profile_reference_requires_confirmed_evidence(self):
        proposed = {}
        calls = self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-013")
        bridge = self.state.questionnaire_bridge
        context = "Retinal screening in adults with diabetes"
        bridge.save_answer("PIP-002", context)
        adapter.save_answer(record, "ACC-013", "Yes")
        self.app.run()
        response = "Yes. The retinal screening population would expand to include adolescents."
        proposed["ACC-017"] = {
            "value": "Yes", "quote": response, "details": response,
            "references": "PIP-002", "reference_evidence": {"PIP-002": context},
        }
        self.submit(f"d23-chat-input-{record}", response)
        key = f"d23-review-{record}-2-ACC-017"
        self.assertEqual(calls[-1]["confirmed_d21_answers"]["PIP-002"], context)
        self.assertIn("Affected profile entries: PIP-002.", self.app.text_area(key=f"{key}-details").value)
        self.assertNotIn("ACC-017", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        self.assertIn("PIP-002", adapter.get_algorithm(record)["answers"]["ACC-017"]["details"])

    def test_future_process_is_not_a_documented_procedure_or_release(self):
        proposed = {}
        self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-021")
        adapter.save_answer(record, "ACC-013", "No")
        self.app.run()
        future = "All modifications will undergo manufacturer-controlled risk assessment, verification, validation, and approval before deployment."
        proposed.update({
            "ACC-021": {"value": "Unknown", "quote": future, "details": future},
            "ACC-029": {"value": "Changes have been made since last release", "quote": future, "details": future},
            "ACC-023": {"value": "Verification and validation were performed.", "quote": future},
        })
        key = f"d23-chat-input-{record}"
        self.submit(key, future)
        self.assertFalse(self.state.d23_conversations[record]["candidates"])
        self.assertTrue(any("already documented in an approved procedure" in node.value for node in self.app.markdown))
        proposed.clear()
        self.submit(key, "I don't know. The quality team cannot provide the procedure record yet.")
        self.assertNotIn("ACC-021", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-021"]["value"], "Unknown")
        self.assertTrue(any("How is each change assessed" in node.value for node in self.app.markdown))

    def test_conflicting_deployed_behavior_requests_clarification_without_overwrite(self):
        proposed = {}
        self.mock_proposals("D2.3", proposed)
        adapter, record = self.start_algorithm_at("ACC-009")
        quote = "The model weights change at the site without a new release."
        proposed["ACC-009"] = {"value": ["Model weights"], "quote": quote}
        key = f"d23-chat-input-{record}"
        self.submit(key, quote)
        self.assertFalse(self.state.d23_conversations[record]["candidates"])
        self.assertTrue(any("without a new manufacturer release, or only between releases" in node.value
                            for node in self.app.markdown))
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-008"]["value"], LOCKED)
        clarification = "No elements change without a new release. We retrain offline between releases."
        proposed["ACC-009"] = {"value": ["None"], "quote": clarification}
        self.submit(key, clarification)
        self.click("Confirm suggestion")
        answers = adapter.get_algorithm(record)["answers"]
        self.assertEqual(answers["ACC-009"]["value"], ["None"])
        self.assertEqual(answers["ACC-008"]["value"], LOCKED)

    def test_natural_release_history_correction_requires_confirmation(self):
        self.mock_proposals("D2.3", {})
        adapter, record = self.start_algorithm_at("ACC-021")
        adapter.save_answer(record, "ACC-029", "None")
        self.app.run()
        self.submit(f"d23-chat-input-{record}", "Actually, we haven't released this algorithm yet.")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-029"]["value"], "None")
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-029"]["value"],
                         "Not applicable (not previously released)")

    def test_component_details_use_original_message_and_keep_evidence_blank(self):
        proposed = {}
        calls = self.mock_proposals("D2.3", proposed)
        self.submit("ux_d23_proposal-message", RETINAGUARD)
        self.click("Confirm algorithm record")
        adapter = self.state.d23_adapter
        record = adapter.algorithm_ids[0]
        adapter.save_answer(record, "ACC-002", "AIF-004")
        adapter.save_answer(record, "ACC-003", [BY_ID["ACC-003"]["options"][0]])
        adapter.save_answer(record, "ACC-004", ["CNN"])
        self.app.run()
        source_id = "2"
        proposed["ACC-005"] = {"value": "Yes", "quote": "Yes", "details": "Uses an invented version."}
        self.submit(f"d23-chat-input-{record}", "Yes. We might use an open-source library in the future.")
        key = f"d23-review-{record}-{source_id}-ACC-005"
        self.assertEqual(self.app.text_area(key=f"{key}-details").value, "")
        self.assertTrue(any("couldn't verify an explanation" in node.value for node in self.app.caption))
        self.click("Confirm suggestion")
        self.assertTrue(any("Enter the component explanation" in node.value for node in self.app.error))
        self.assertNotIn("ACC-005", adapter.get_algorithm(record)["answers"])
        self.click("Reject suggestion")
        proposed["ACC-005"].pop("details")
        self.submit(f"d23-chat-input-{record}", COMPONENT_DESCRIPTION)
        key = f"d23-review-{record}-3-ACC-005"
        self.assertEqual(self.app.text_area(key=f"{key}-details").value, COMPONENT_DESCRIPTION[5:])
        self.assertEqual(self.app.text_input(key=f"{key}-evidence").value, "")
        self.assertNotIn("ACC-005", adapter.get_algorithm(record)["answers"])
        self.click("Confirm suggestion")
        self.assertEqual(adapter.get_algorithm(record)["answers"]["ACC-005"], {
            "value": "Yes", "details": COMPONENT_DESCRIPTION[5:], "evidence": "",
        })
        self.assertEqual(len(calls), 3)

    def test_gemini_error_retains_turn_and_offers_focused_followup(self):
        self.submit("ux_d23_proposal-message", RETINAGUARD)
        self.click("Confirm algorithm record")
        record = self.state.d23_active_algorithm_id
        self.d23_extractor.side_effect = RuntimeError("Unavailable")
        self.submit(f"d23-chat-input-{record}", FUNCTION_DESCRIPTION)
        self.app.run()
        self.assertTrue(any("Your message is retained" in node.value for node in self.app.markdown))
        self.assertTrue(any("Which confirmed AI-function entries" in node.value for node in self.app.markdown))
        self.assertEqual(self.state.d23_conversations[record]["turns"].count(FUNCTION_DESCRIPTION), 1)

    def test_algorithm_name_and_version_can_arrive_in_separate_turns(self):
        self.submit("ux_d23_proposal-message", "Our algorithm is called Retinal Screening.")
        self.assertTrue(any("What version of Retinal Screening" in node.value for node in self.app.markdown))
        self.assertFalse(self.state.d23_adapter.algorithm_ids)
        self.submit("ux_d23_proposal-message", "The version is 2.4.")
        self.assertFalse(self.state.d23_adapter.algorithm_ids)
        self.click("Confirm algorithm record")
        record = self.state.d23_adapter.get_algorithm(self.state.d23_active_algorithm_id)
        self.assertEqual((record["name"], record["version"]), ("Retinal Screening", "2.4"))
        self.assertIn("The version is 2.4.", self.d23_extractor.call_args.args[0])

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
        self.assertTrue(any("Which of the AI functions" in item.value for item in self.app.markdown))
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
