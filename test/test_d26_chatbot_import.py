import copy
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest


ENTRY_POINT = Path(__file__).resolve().parents[1] / (
    "app/deliverable_2/integration/run_integrated_profile.py"
)


class D26ChatBuddyImportTests(unittest.TestCase):
    def setUp(self):
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
        self.app.file_uploader[0].set_value(
            ("chat-buddy.json", json.dumps(profile).encode("utf-8"), "application/json")
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
