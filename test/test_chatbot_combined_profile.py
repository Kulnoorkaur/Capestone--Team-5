import json
from pathlib import Path
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.d23_adapter import D23AnswerAdapter
from app.chatbot.profile_io import (
    COMBINED_SCHEMA,
    COMBINED_VERSION,
    ProfileImportError,
    dump_combined_profile,
    load_combined_profile,
    load_confirmed_profile,
)
from app.chatbot.questionnaire_bridge import QuestionnaireBridge
from app.deliverable_2.questionnaires.algorithm_change_control import ADAPTIVE, LOCKED


CHAT_APP = Path(__file__).resolve().parents[1] / "app/chatbot/chat_app.py"


def answer(value, details="", evidence=""):
    return {"value": value, "details": details, "evidence": evidence}


def record(algorithm_id, answers):
    return {"algorithm_id": algorithm_id, "name": "Demo model", "version": "1.0", "answers": answers}


def combined(*algorithms, product=None, ai_function=None):
    return json.dumps({
        "schema": COMBINED_SCHEMA, "version": COMBINED_VERSION,
        "product": product or {}, "ai_function": ai_function or {},
        "algorithms": list(algorithms),
    })


class CombinedProfileTests(unittest.TestCase):
    def test_empty_profile_and_legacy_loader_contract(self):
        profile = load_combined_profile(combined())
        self.assertEqual(profile.bridge.get_product_profile(), {})
        self.assertEqual(profile.algorithms.algorithm_ids, ())
        self.assertEqual(json.loads(dump_combined_profile(profile.bridge)), json.loads(combined()))
        self.assertEqual(load_confirmed_profile('{"PIP-001":"Demo","AIF-019":"No"}'), {
            "product": {"PIP-001": "Demo"}, "ai_function": {"AIF-019": "No"},
        })

    def test_multiple_records_round_trip_and_edits_are_isolated(self):
        parent_answers = {
            "ACC-001": answer("Demo model V1"),
            "ACC-002": answer("AIF-004"),
            "ACC-003": answer(["Supervised"]),
            "ACC-008": answer(ADAPTIVE),
            "ACC-010": answer("Learning requires human approval.", evidence="Design v1, §4"),
            "ACC-013": answer("Yes"),
            "ACC-019": answer("Yes", details="Documented plan"),
            "ACC-020": answer({"FDA": "Under review", "Health Canada": None}, evidence="Plan V1, §2"),
        }
        profile = load_combined_profile(combined(
            record("algorithm-2", dict(reversed(tuple(parent_answers.items())))),
            record("algorithm-1", {"ACC-008": answer(LOCKED)}),
            product={"PIP-009": "Yes", "TRAINING-DETAILS": "Onboarding"},
            ai_function={"AIF-001": ["Medical images"], "AIF-019": "No"},
        ).encode())
        algorithms = profile.algorithms
        self.assertEqual(algorithms.algorithm_ids, ("algorithm-2", "algorithm-1"))
        first = algorithms.get_algorithm("algorithm-2")
        self.assertEqual(first["answers"], parent_answers)
        self.assertEqual(first["name"], algorithms.get_algorithm("algorithm-1")["name"])
        self.assertEqual(first["version"], "1.0")
        self.assertIn("ACC-020", algorithms.active_field_ids("algorithm-2"))

        exported = dump_combined_profile(profile.bridge, algorithms)
        restored = load_combined_profile(exported)
        self.assertEqual(exported, dump_combined_profile(restored.bridge, restored.algorithms))
        for algorithm_id in algorithms.algorithm_ids:
            self.assertEqual(algorithms.build_record(algorithm_id), restored.algorithms.build_record(algorithm_id))
        second = restored.algorithms.get_algorithm("algorithm-1")
        restored.algorithms.save_answer("algorithm-2", "ACC-013", "No")
        self.assertNotIn("ACC-020", restored.algorithms.get_algorithm("algorithm-2")["answers"])
        self.assertEqual(restored.algorithms.get_algorithm("algorithm-1"), second)
        self.assertNotIn(restored.algorithms.add_algorithm("Third record"), algorithms.algorithm_ids)

    def test_quotes_omitted_and_missing_documentation_is_recomputed(self):
        algorithms = D23AnswerAdapter()
        algorithm_id = algorithms.add_algorithm("Demo")
        algorithms.save_answer(algorithm_id, "ACC-005", "Yes", source_quote="Uses a third-party model.")
        original = algorithms.build_record(algorithm_id)
        raw = dump_combined_profile(QuestionnaireBridge(), algorithms)
        self.assertNotIn("source_quotes", raw)
        self.assertNotIn("Uses a third-party model", raw)
        restored = load_combined_profile(raw).algorithms
        self.assertEqual(restored.get_algorithm(algorithm_id)["source_quotes"], {})
        self.assertEqual(restored.build_record(algorithm_id), original)
        self.assertTrue(any(f["flag_id"] == "FLG-10" for f in original["flags"]))
        self.assertTrue(any(p["id"] == "ACC-005" for p in original["validation_problems"]))

    def test_invalid_files_are_rejected(self):
        cases = (
            ("{", "Invalid JSON"),
            ("{}", "Expected a Chat Buddy combined profile"),
            (combined().replace('"version": 1', '"version": 2'), "Unsupported combined profile version"),
            (combined().replace('"version": 1', '"version": true'), "Unsupported combined profile version"),
            (combined(record("same", {}), record("same", {})), "Duplicate algorithm ID"),
            (combined(record("", {})), "Algorithm ID must be non-empty"),
            (combined(record("a", {"ACC-999": answer("Yes")})), "Unknown D2.3 field IDs"),
            (combined(record("a", {"ACC-008": answer("Invalid")})), "ACC-008: Expected an allowed option"),
            (combined(record("a", {"ACC-004": answer("CNN")})), "ACC-004: Expected a non-empty list"),
            (combined(record("a", {"ACC-010": answer("Inactive")})), "ACC-010: This conditional question is inactive"),
            (combined(record("a", {"ACC-013": answer("Unknown"), "ACC-019": answer("Yes"),
                                    "ACC-020": answer({"FDA": "Under review"})})), "ACC-019: This conditional"),
            (combined(record("a", {"ACC-013": answer("Yes"), "ACC-019": answer("Yes"),
                                    "ACC-020": answer({"FDA": "Invalid"})})), "ACC-020: Invalid status"),
            (combined(product={"AIF-019": "No"}), "wrong questionnaire section"),
            (combined(ai_function={"AIF-019": "Invalid"}), "AIF-019: Invalid dropdown option"),
            (combined(product={"PIP-009": "No", "TRAINING-DETAILS": "Inactive"}), "TRAINING-DETAILS: This conditional"),
        )
        for raw, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ProfileImportError, message):
                load_combined_profile(raw)


class CombinedProfileStreamlitTests(unittest.TestCase):
    def test_preview_and_invalid_restore_are_non_destructive(self):
        with patch.object(chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")) as gemini:
            app = AppTest.from_file(str(CHAT_APP), default_timeout=25).run()
            self.assertFalse(app.exception)
            state = app.session_state
            original_bridge = state.questionnaire_bridge
            self.assertTrue(original_bridge.save_answer("PIP-001", "Old product")[0])
            self.assertTrue(original_bridge.save_answer("AIF-019", "Yes")[0])
            original_algorithms = D23AnswerAdapter()
            original_algorithms.add_algorithm("Old model")
            original_algorithms.save_answer(
                "algorithm-1", "ACC-008", LOCKED, source_quote="Old confirmed quote."
            )
            old_record = original_algorithms.get_algorithm("algorithm-1")
            state.d23_adapter = original_algorithms
            state.d23_active_algorithm_id = "algorithm-1"
            state.d23_answer_revision = 0
            state.d23_mode = True
            candidate = {
                "algorithm_id": "algorithm-1", "source_id": "1", "value": "Old draft",
                "details": "", "quote": "Old suggested quote.",
            }
            state.d23_conversations = {"algorithm-1": {
                "turns": [candidate["quote"]], "candidates": {"ACC-001": candidate},
                "rejected": {"ACC-001": {("old draft", "old suggested quote.")}},
                "skipped": set(), "notice": "",
            }}
            state.field_suggestions = {"PIP-002": "Pending suggestion"}
            state.carryover["turns"]["1"] = {"message": "Old turn"}
            state.carryover["rejected"]["PIP-002"] = {("old turn", "old turn")}
            state.retryable_turn = {
                "message": "Pending retry", "context": ("D2.1", None, None), "source_id": "1",
            }
            state.unrelated = "Keep this"

            def upload(raw):
                app.run()
                app.file_uploader(key="combined_profile_upload").set_value(
                    ("combined.json", raw.encode(), "application/json")
                ).run()
                self.assertFalse(app.exception)

            replacement = combined(
                record("algorithm-1", {"ACC-008": answer(LOCKED, evidence="Design v1, §4")}),
                record("algorithm-9", {"ACC-008": answer(ADAPTIVE)}),
                product={"PIP-001": "New product"}, ai_function={"AIF-019": "No"},
            )
            invalid = combined(record("algorithm-9", {"ACC-008": answer(LOCKED)}),
                               record("algorithm-10", {"ACC-010": answer("Inactive")}),
                               product={"PIP-001": "New product"})
            upload(invalid)
            self.assertTrue(any("ACC-010" in error.value for error in app.error))
            self.assertNotIn("Restore combined profile", [button.label for button in app.button])
            self.assertIs(state.questionnaire_bridge, original_bridge)
            self.assertIs(state.d23_adapter, original_algorithms)
            self.assertEqual(state.d23_active_algorithm_id, "algorithm-1")
            self.assertEqual(original_algorithms.get_algorithm("algorithm-1"), old_record)
            self.assertEqual(original_bridge.get_questionnaire_answers("D2.2"), {"AIF-019": "Yes"})
            self.assertEqual(state.field_suggestions, {"PIP-002": "Pending suggestion"})
            self.assertEqual(state.d23_conversations["algorithm-1"]["candidates"], {"ACC-001": candidate})
            self.assertEqual(state.retryable_turn["message"], "Pending retry")

            upload(replacement)
            self.assertIs(state.questionnaire_bridge, original_bridge)
            self.assertIs(state.d23_adapter, original_algorithms)
            self.assertEqual(state.d23_active_algorithm_id, "algorithm-1")
            self.assertTrue(any("Demo model" in element.value for element in app.text))
            # Send an old review click in the same run as the restore click.
            stale_key = "d23-review-algorithm-1-1-ACC-001"
            app.text_input(key=stale_key).set_value("Edited stale draft")
            app.button(key=f"{stale_key}-confirm").click()
            next(button for button in app.button if button.label == "Restore combined profile").click().run()
            self.assertFalse(app.exception)
            expected_flat = {"PIP-001": "New product", "AIF-019": "No"}
            self.assertEqual(state.questionnaire_bridge.get_product_profile(), expected_flat)
            self.assertEqual(state.d23_adapter.algorithm_ids, ("algorithm-1", "algorithm-9"))
            self.assertNotIn("d23_active_algorithm_id", state)
            restored_record = state.d23_adapter.get_algorithm("algorithm-1")
            self.assertEqual(restored_record["answers"], {
                "ACC-008": answer(LOCKED, evidence="Design v1, §4"),
            })
            self.assertEqual(restored_record["source_quotes"], {})
            self.assertNotIn(f"{stale_key}-confirm", [button.key for button in app.button])
            self.assertNotIn(stale_key, state)
            self.assertEqual(state.field_suggestions, {})
            self.assertEqual(state.d23_conversations, {})
            self.assertEqual(state.carryover["turns"], {})
            self.assertEqual(state.carryover["rejected"], {})
            self.assertIsNone(state.retryable_turn)
            self.assertEqual(state.unrelated, "Keep this")
            self.assertEqual(state.asked_field, "PIP-002")

            with patch.object(st, "download_button", wraps=st.download_button) as downloads:
                app.run()
            calls = {call.args[0]: call.kwargs for call in downloads.call_args_list}
            self.assertEqual(json.loads(calls["Download combined D2.1–D2.3 JSON"]["data"]), json.loads(replacement))
            self.assertEqual(json.loads(calls["Export Confirmed Profile"]["data"]), expected_flat)
            fresh = AppTest.from_file(str(CHAT_APP), default_timeout=25).run()
            fresh.file_uploader(key="combined_profile_upload").set_value((
                "combined.json", calls["Download combined D2.1–D2.3 JSON"]["data"].encode(),
                "application/json",
            )).run()
            next(button for button in fresh.button if button.label == "Restore combined profile").click().run()
            self.assertFalse(fresh.exception)
            with patch.object(st, "download_button", wraps=st.download_button) as fresh_downloads:
                fresh.run()
            self.assertEqual(
                next(call.kwargs["data"] for call in fresh_downloads.call_args_list
                     if call.args[0] == "Download combined D2.1–D2.3 JSON"),
                calls["Download combined D2.1–D2.3 JSON"]["data"],
            )
            gemini.assert_not_called()
