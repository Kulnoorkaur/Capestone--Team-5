import copy
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from app.chatbot import chat_llm
from app.chatbot.d23_adapter import D23AnswerAdapter
from app.chatbot.d24_adapter import D24AnswerAdapter
from app.chatbot.profile_io import dump_combined_profile
from app.chatbot.questionnaire_bridge import QuestionnaireBridge
from app.deliverable_2.questionnaires.algorithm_change_control import LOCKED, build_record


ENTRY_POINT = Path(__file__).resolve().parents[1] / (
    "app/deliverable_2/integration/run_integrated_profile.py"
)


class D26ChatBuddyImportTests(unittest.TestCase):
    def setUp(self):
        self.gemini = self.enterContext(patch.object(
            chat_llm, "get_gemini_client", side_effect=AssertionError("Unexpected Gemini call")
        ))
        self.addCleanup(self.gemini.assert_not_called)
        self.app = AppTest.from_file(str(ENTRY_POINT), default_timeout=30).run()
        self.assert_no_app_errors()

    def assert_no_app_errors(self):
        self.assertFalse(self.app.exception, [error.message for error in self.app.exception])

    def button(self, label):
        return next(button for button in self.app.button if button.label == label)

    def click(self, label):
        self.button(label).click().run()
        self.assert_no_app_errors()

    def upload(self, profile):
        raw = profile if isinstance(profile, str) else json.dumps(profile)
        self.app.file_uploader[0].set_value(
            ("chat-buddy.json", raw.encode("utf-8"), "application/json")
        ).run()
        self.assert_no_app_errors()

    def evaluate(self):
        assessed_profiles = []

        def capture_assessment(frame, event, _arg):
            if event == "call" and frame.f_code.co_name == "assess" and (
                frame.f_code.co_filename == str(ENTRY_POINT)
            ):
                assessed_profiles.append(copy.deepcopy(frame.f_locals["profile"]))

        # AppTest executes the real entry point on a new thread. Observe the
        # assessment argument and download payload while leaving both calls intact.
        previous_profiler = threading.getprofile()
        threading.setprofile(capture_assessment)
        try:
            with patch.object(st, "download_button", wraps=st.download_button) as downloads:
                self.click("Evaluate integrated profile")
        finally:
            threading.setprofile(previous_profiler)

        self.assertEqual(len(assessed_profiles), 1)
        profile = assessed_profiles[0]
        self.assertEqual(self.app.session_state["d26-profile"], profile)
        self.assertTrue(self.app.session_state["d26-results"]["frameworks"])
        profile_downloads = [
            args[1]
            for args, _ in downloads.call_args_list
            if args and args[0] == "Download integrated profile (JSON)"
        ]
        self.assertEqual(len(profile_downloads), 1)
        self.assertEqual(json.loads(profile_downloads[0]), json.loads(json.dumps(profile, default=str)))
        self.assertTrue(self.app.get("download_button"))
        return profile

    def assert_results_cleared(self):
        self.assertNotIn("d26-profile", self.app.session_state)
        self.assertNotIn("d26-results", self.app.session_state)
        self.assertFalse(self.app.get("download_button"))

    def test_evaluation_and_download_follow_selected_answer_source(self):
        manual_name = "Demo imaging AI, manual draft"
        imported_name = "Demo imaging AI, Version 1.0"
        self.app.text_input(key="PIP-001").set_value(manual_name)
        self.app.selectbox(key="PIP-006").select("CT")
        self.app.selectbox(key="AIF-019").select("Yes")
        self.app.multiselect(key="AIF-001").set_value(["Clinical metadata"])
        self.app.text_input(key="d26-model-0-name").set_value("Demo model V1")
        self.app.text_input(key="dataset-0-DEP-001-name").set_value("Demo dataset V1")
        hazards = next(
            field for field in self.app.text_area
            if field.label == "Identify known or anticipated product-related risks or hazards."
        )
        hazards.set_value("Delayed result review")
        self.app.multiselect(key="d26-INT-001").set_value(["Canada"])
        self.app.run()
        self.assert_no_app_errors()
        manual = self.evaluate()
        self.assertEqual(manual["product"]["PIP-001"], manual_name)
        self.assertEqual(manual["product"]["PIP-006"], "CT")
        self.assertEqual(manual["ai_function"]["AIF-019"], "Yes")
        self.assertEqual(manual["ai_function"]["AIF-001"], ["Clinical metadata"])
        self.assertIn("Demo model V1", json.dumps(manual["algorithms"]))
        self.assertIn("Demo dataset V1", json.dumps(manual["dataset_evidence"]))
        self.assertEqual(manual["risk_documentation"]["RCD-002"], "Delayed result review")
        self.assertEqual(manual["integration"]["INT-001"], ["Canada"])

        product = {
            "PIP-001": imported_name,
            "PIP-006": "Other",
            "PIP-006-OTHER": "Retinal fundus photography",
        }
        ai_function = {"AIF-019": "No"}
        self.upload({**product, **ai_function})
        self.assertTrue(any("Valid Chat Buddy export" in status.value for status in self.app.success))
        previews = [json.loads(element.value) for element in self.app.json]
        self.assertIn(product, previews)
        self.assertIn(ai_function, previews)
        self.assertEqual(self.app.session_state["d26-profile"], manual)
        self.assertTrue(self.app.get("download_button"))

        self.click("Use this profile")
        self.assert_results_cleared()
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        imported = self.evaluate()
        self.assertEqual(imported["product"], product)
        self.assertEqual(imported["ai_function"], ai_function)
        for section in ("algorithms", "dataset_evidence", "risk_documentation", "integration"):
            self.assertEqual(imported[section], manual[section])

        self.upload({"PIP-001": "Demo imaging AI, Version 2.0", "AIF-019": "No"})
        self.assertEqual(self.app.session_state["d26-profile"], imported)
        self.assertTrue(self.app.get("download_button"))
        self.click("Use this profile")
        self.assert_results_cleared()
        self.assertFalse(self.app.checkbox(key="d26-retained-inputs-ack").value)
        self.assertTrue(self.button("Evaluate integrated profile").disabled)

        self.click("Use manual answers")
        self.assert_results_cleared()
        self.assertFalse(self.button("Evaluate integrated profile").disabled)
        self.assertEqual(self.evaluate(), manual)

    def test_combined_import_and_independent_algorithm_source(self):
        def answer(value, details="", evidence=""):
            return {"value": value, "details": details, "evidence": evidence}

        self.app.text_input(key="d26-model-0-name").set_value("Manual model")
        self.app.selectbox(key="d26-model-0-ACC-008").select(LOCKED)
        self.app.text_input(key="d26-model-0-ACC-008-evidence").set_value("Design v1 §4")
        self.app.selectbox(key="d26-model-0-ACC-013").select("Yes").run()
        self.app.selectbox(key="d26-model-0-ACC-019").select("Yes").run()
        self.app.text_area(key="d26-model-0-ACC-019-details").set_value("Change plan §1")
        self.app.selectbox(key="d26-model-0-ACC-020-FDA").select("Under review").run()
        manual = self.evaluate()
        manual_results = copy.deepcopy(self.app.session_state["d26-results"])
        manual_record = manual["algorithms"][0]

        answers = {
            "ACC-008": answer(LOCKED, evidence="Design v1 §4"),
            "ACC-013": answer("Yes"),
            "ACC-019": answer("Yes", "Change plan §1"),
            "ACC-020": answer({"FDA": "Under review"}),
        }
        bridge = QuestionnaireBridge()
        self.assertTrue(bridge.save_answer("PIP-001", "Imported product v1")[0])
        self.assertTrue(bridge.save_answer("AIF-019", "No")[0])
        adapter = D23AnswerAdapter()
        first_id = adapter.add_algorithm("Same model", "1", algorithm_id="model-a")
        second_id = adapter.add_algorithm("Same model", "2", algorithm_id="model-b")
        for field_id, confirmed in answers.items():
            adapter.save_answer(first_id, field_id, **confirmed)
        adapter.save_answer(second_id, "ACC-005", "Yes")
        adapter.save_answer(second_id, "ACC-001", "Second model", evidence="Model register §2")
        exported = dump_combined_profile(bridge, adapter)
        combined = json.loads(exported)
        first, second = combined["algorithms"]
        self.upload(exported)
        self.assertIn("D2.3 Algorithm/change — 2 records", [item.label for item in self.app.expander])
        self.assertTrue(any("Same model — 2 (model-b)" in item.value for item in self.app.text))
        self.assertTrue(any("questionnaire validation gaps" in item.value for item in self.app.warning))
        self.assertEqual(self.app.session_state["d26-profile"], manual)
        self.assertEqual(self.app.session_state["d26-results"], manual_results)

        self.click("Use this profile")
        self.assert_results_cleared()
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        imported = self.evaluate()
        self.assertEqual(imported.keys(), manual.keys())
        self.assertEqual(imported["schema_version"], "D2.6-V1")
        self.assertEqual(self.app.session_state["d26-results"].keys(), manual_results.keys())
        self.assertEqual(imported["product"], combined["product"])
        self.assertEqual(imported["ai_function"], combined["ai_function"])
        for section in ("dataset_evidence", "risk_documentation", "integration"):
            self.assertEqual(imported[section], manual[section])
        self.assertEqual([model["algorithm_id"] for model in imported["algorithms"]], ["model-a", "model-b"])
        self.assertEqual([model["version"] for model in imported["algorithms"]], ["1", "2"])
        model, partial = imported["algorithms"]
        native = build_record("Same model — 1", answers)
        self.assertEqual({key: model[key] for key in native}, native)
        for key in ("validation_problems", "flags", "profile_status", "not_applicable"):
            self.assertEqual(model[key], manual_record[key])
        for field_id in ("ACC-008", "ACC-013", "ACC-019"):
            self.assertEqual(model["answers"][field_id], manual_record["answers"][field_id])
        self.assertEqual(model["answers"]["ACC-020"]["value"], {
            fw: status for fw, status in manual_record["answers"]["ACC-020"]["value"].items() if status
        })
        self.assertEqual(partial["answers"]["ACC-008"], answer(None))
        self.assertEqual(partial["answers"]["ACC-001"], answer("Second model", evidence="Model register §2"))
        self.assertNotEqual(model["answers"]["ACC-001"], partial["answers"]["ACC-001"])
        self.assertNotIn("ACC-020", partial["answers"])
        self.assertTrue(any(issue["id"] == "ACC-005" for issue in partial["validation_problems"]))
        self.assertTrue(any(
            issue["issue_id"].startswith("D26-ACC-2-ACC-005")
            for issue in self.app.session_state["d26-results"]["issue_log"]
        ))

        self.upload({**combined, "algorithms": [first, first]})
        self.assertTrue(any("Duplicate algorithm ID" in issue.value for issue in self.app.error))
        self.assertNotIn("Use this profile", [button.label for button in self.app.button])
        self.assertEqual(self.app.session_state["d26-profile"], imported)
        self.assertTrue(self.app.get("download_button"))

        self.click("Use manual D2.3 records")
        self.assert_results_cleared()
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        self.assertEqual(self.evaluate(), {**imported, "algorithms": manual["algorithms"]})
        self.click("Use imported D2.3 records")
        self.assert_results_cleared()
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.upload({**combined, "algorithms": [second]})
        self.click("Use this profile")
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        self.assertEqual(self.evaluate()["algorithms"], [partial])
        self.upload({"PIP-001": "Legacy product"})
        self.click("Use this profile")
        self.assert_results_cleared()
        self.assertNotIn("Use imported D2.3 records", [button.label for button in self.app.button])
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        self.assertEqual(self.evaluate()["algorithms"], manual["algorithms"])

    def test_version_two_import_projects_native_d24_and_preserves_source_isolation(self):
        self.app.text_input(key="d26-model-0-name").set_value("Manual model")
        self.app.text_input(key="dataset-0-DEP-001-name").set_value("Manual dataset draft")
        self.app.text_input(key="document-0-id").set_value("Manual evidence draft")
        self.app.run()
        manual = self.evaluate()
        manual_results = copy.deepcopy(self.app.session_state["d26-results"])
        bridge = QuestionnaireBridge()
        self.assertTrue(bridge.save_answer("PIP-001", "Demo product v2")[0])
        self.assertTrue(bridge.save_answer("AIF-019", "No")[0])
        algorithms = D23AnswerAdapter()
        algorithms.add_algorithm("Imported model", "2", algorithm_id="model-a")
        algorithms.add_algorithm("Imported model", "2.1", algorithm_id="model-b")
        adapter = D24AnswerAdapter()
        for index in (1, 2):
            dataset = adapter.create_record("dataset")
            adapter.save_answer(dataset, "DEP-001.dataset_name_version", f"Cohort {index}")
            adapter.save_answer(dataset, "DEP-001.role", ["Other"])
            adapter.save_answer(dataset, "DEP-001.role_other", f"Calibration cohort {index}")
            adapter.save_answer(dataset, "DEP-003", "Unknown")
            evaluation = adapter.create_record("function")
            adapter.save_answer(evaluation, "DEP-019-versions", f"Model v2.{index}")
            adapter.save_answer(evaluation, "DEP-028", ["Literature only"])
            adapter.save_answer(evaluation, "DEP-033", "Published evidence review")
            document = adapter.create_record("document")
            adapter.save_answer(document, "document_id", f"Reference {index}")
        adapter.save_answer(adapter.GMLP, "DEP-036-trigger", "Yes")
        adapter.save_answer(adapter.GMLP, "DEP-036", "Partly")
        adapter.save_answer(adapter.GMLP, "DEP-036-document", "Reference 1 §2")
        backup = dump_combined_profile(bridge, algorithms, dataset_evidence=adapter)
        expected = adapter.native_profile()

        self.upload(backup)
        self.assertTrue(any("2 datasets, 2 evaluation records, 2 supporting documents" in item.value
                            for item in self.app.caption))
        self.assertIn(expected, [json.loads(item.value) for item in self.app.json])
        self.assertTrue(any("D2.4 questionnaire has validation findings" in item.value for item in self.app.warning))
        self.assertEqual(self.app.session_state["d26-profile"], manual)
        self.assertEqual(self.app.session_state["d26-results"], manual_results)
        self.assertTrue(self.app.get("download_button"))
        self.assertNotIn("d26-chatbot-profile", self.app.session_state)

        self.click("Use this profile")
        self.assert_results_cleared()
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        imported = self.evaluate()
        imported_results = copy.deepcopy(self.app.session_state["d26-results"])
        self.assertEqual(imported.keys(), manual.keys())
        self.assertEqual(imported_results.keys(), manual_results.keys())
        self.assertEqual(imported["dataset_evidence"], expected)
        self.assertEqual(imported["product"]["PIP-001"], "Demo product v2")
        self.assertEqual(imported["ai_function"]["AIF-019"], "No")
        self.assertEqual(imported["algorithms"][0]["record_name"], "Imported model — 2")
        self.assertEqual([model["algorithm_id"] for model in imported["algorithms"]], ["model-a", "model-b"])
        self.assertEqual(self.app.session_state["d26-chatbot-profile"]["dataset_findings"], adapter.validate())
        findings_view = next(item for item in self.app.expander
                             if item.label == "D2.4 validation findings for the assessed profile")
        self.assertEqual(
            json.loads(findings_view.get("dataframe")[0].value.to_json(orient="records")),
            adapter.validate(),
        )
        self.assertEqual(expected["datasets"][0]["DEP-001"]["dataset_name_version"], "Cohort 1")
        self.assertEqual(expected["datasets"][1]["DEP-001"]["role_other"], "Calibration cohort 2")
        self.assertEqual(expected["datasets"][0]["DEP-003"], "Unknown")
        self.assertEqual(expected["datasets"][0]["DEP-005"], "")
        self.assertEqual(expected["ai_function_versions"][1]["DEP-033"], "Published evidence review")
        self.assertEqual(expected["DEP-036-document"], "Reference 1 §2")
        for collection in ("datasets", "ai_function_versions", "evidence_documents"):
            self.assertTrue(all("record_id" not in record for record in expected[collection]))

        cases = (
            (("dataset_evidence", "datasets", 0, "answers", "DEP-999"), "Unknown", "Unknown field IDs"),
            (("dataset_evidence", "datasets", 0, "answers", "DEP-003"), "Unsupported", "allowed option"),
            (("dataset_evidence", "datasets", 0, "answers", "DEP-012"), "Inactive", "inactive field"),
            (("dataset_evidence", "datasets", 1, "record_id"), "dataset-1", "Duplicate D2.4 record ID"),
            (("dataset_evidence", "questionnaire_sha256"), "unreviewed", "compatibility manifest requires review"),
            (("version",), 9, "Unsupported combined profile version"),
        )
        for path, value, diagnostic in cases:
            with self.subTest(path=path):
                invalid = json.loads(backup)
                destination = invalid
                for key in path[:-1]:
                    destination = destination[key]
                destination[path[-1]] = value
                self.upload(invalid)
                self.assertTrue(any(diagnostic in item.value for item in self.app.error))
                self.assertNotIn("Use this profile", [button.label for button in self.app.button])
                self.assertEqual(self.app.session_state["d26-profile"], imported)
                self.assertEqual(self.app.session_state["d26-results"], imported_results)
                self.assertTrue(self.app.get("download_button"))
                self.assertEqual(self.app.text_input(key="dataset-0-DEP-001-name").value, "Manual dataset draft")
                self.assertEqual(self.app.text_input(key="d26-model-0-name").value, "Manual model")

        self.click("Use manual D2.3 records")
        self.assert_results_cleared()
        self.assertTrue(self.app.session_state["d26-use-chatbot-dataset_evidence"])
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        self.assertEqual(self.evaluate(), {**imported, "algorithms": manual["algorithms"]})

        self.click("Use manual D2.4 records")
        self.assert_results_cleared()
        self.assertFalse(self.app.session_state["d26-use-chatbot-algorithms"])
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        self.assertEqual(self.evaluate(), {
            **imported, "algorithms": manual["algorithms"], "dataset_evidence": manual["dataset_evidence"],
        })
        self.click("Use imported D2.3 records")
        self.assert_results_cleared()
        self.assertFalse(self.app.session_state["d26-use-chatbot-dataset_evidence"])
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        manual_d24 = self.evaluate()
        self.assertEqual(manual_d24, {**imported, "dataset_evidence": manual["dataset_evidence"]})
        self.assertEqual(self.app.text_input(key="document-0-id").value, "Manual evidence draft")

        self.upload(dump_combined_profile(bridge, algorithms))
        self.assertEqual(self.app.session_state["d26-profile"], manual_d24)
        self.assertTrue(self.app.get("download_button"))
        self.click("Use this profile")
        self.assert_results_cleared()
        self.assertFalse(any("D2.4 records" in button.label for button in self.app.button))
        self.assertTrue(self.button("Evaluate integrated profile").disabled)
        self.app.checkbox(key="d26-retained-inputs-ack").check().run()
        self.assertEqual(self.evaluate()["dataset_evidence"], manual["dataset_evidence"])
