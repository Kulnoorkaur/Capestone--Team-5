import json
import unittest

from app.chatbot.profile_io import ProfileImportError, load_confirmed_profile
from app.chatbot.questionnaire_bridge import (
    CONDITIONAL_FIELDS,
    QUESTIONNAIRE_FIELDS,
    QuestionnaireBridge,
)


class ProfileImportTests(unittest.TestCase):
    def test_load_complete_export_with_children_before_parents(self):
        bridge = QuestionnaireBridge()
        triggers = {
            parent: trigger[0] if isinstance(trigger, tuple) else trigger
            for parent, trigger in CONDITIONAL_FIELDS.values()
        }
        expected = {}
        for questionnaire, section in (("D2.1", "product"), ("D2.2", "ai_function")):
            answers = {}
            for field_id in QUESTIONNAIRE_FIELDS[questionnaire]:
                options = bridge.get_field_options(field_id)
                value = triggers.get(field_id, options[0] if options else f"Answer for {field_id}")
                answers[field_id] = [value] if bridge.get_field_type(field_id) == "multiselect" else value
            expected[section] = answers

        children = {field_id: f"Detail for {field_id}" for field_id in CONDITIONAL_FIELDS}
        flat = {**children, **expected["product"], **expected["ai_function"]}
        for field_id, (parent, _) in CONDITIONAL_FIELDS.items():
            section = "product" if parent in expected["product"] else "ai_function"
            expected[section][field_id] = children[field_id]

        self.assertEqual(len(flat), 63)
        self.assertEqual(load_confirmed_profile(json.dumps(flat).encode("utf-8")), expected)

    def test_partial_export_preserves_strings_options_and_list_order(self):
        product = {
            "PIP-001": "  Démo AI, Version 1.0  ",
            "PIP-009": "Unknown",
            "PIP-016": ["Outpatient clinic", "Hospital"],
        }
        ai_function = {
            "AIF-001": ["Clinical metadata", "Medical images"],
            "AIF-019": "No",
        }
        self.assertEqual(
            load_confirmed_profile(json.dumps({**product, **ai_function}, ensure_ascii=False)),
            {"product": product, "ai_function": ai_function},
        )

    def test_partial_export_accepts_missing_applicable_follow_up(self):
        self.assertEqual(
            load_confirmed_profile('{"PIP-009": "Yes"}'),
            {"product": {"PIP-009": "Yes"}, "ai_function": {}},
        )

    def test_training_details_belong_in_product_section(self):
        self.assertEqual(
            load_confirmed_profile('{"TRAINING-DETAILS": "Onboarding", "PIP-009": "Yes"}'),
            {"product": {"PIP-009": "Yes", "TRAINING-DETAILS": "Onboarding"}, "ai_function": {}},
        )

    def test_empty_export(self):
        self.assertEqual(load_confirmed_profile("{}"), {"product": {}, "ai_function": {}})

    def test_invalid_export_reports_reason(self):
        cases = [
            ('{"PIP-001":', "Invalid JSON at line 1, column"),
            ("", "Invalid JSON"),
            (b"\xff", "UTF-8"),
            ("[]", "Expected a flat JSON object"),
            ("null", "Expected a flat JSON object"),
            ('{"product": {}}', "Unknown field IDs: product"),
            ('{"AIF-999": "No"}', "Unknown field IDs: AIF-999"),
            ('{"PIP-006": "Unlisted modality"}', "PIP-006: Invalid dropdown option"),
            ('{"AIF-001": ["Medical images", "Unlisted input"]}', "AIF-001: Invalid multiselect option"),
            ('{"PIP-001": ["Demo"]}', "PIP-001: This field requires text"),
            ('{"AIF-001": "Medical images"}', "AIF-001: This field requires a list"),
            ('{"AIF-019": false}', "AIF-019: This field requires a dropdown option"),
            ('{"PIP-001": "  "}', "PIP-001: The answer cannot be empty"),
            ('{"PIP-009": "No", "TRAINING-DETAILS": "Onboarding"}', "TRAINING-DETAILS: This conditional"),
            ('{"AIF-014-DETAILS": "Clinician review"}', "AIF-014-DETAILS: This conditional"),
            ('{"PIP-001": "First", "PIP-001": "Second"}', "Duplicate field ID: PIP-001"),
        ]
        for raw, message in cases:
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ProfileImportError, message):
                    load_confirmed_profile(raw)

    def test_invalid_import_returns_no_partially_loaded_sections(self):
        loaded = load_confirmed_profile('{"PIP-001": "Existing profile"}')
        with self.assertRaisesRegex(ProfileImportError, "AIF-005-DETAILS"):
            loaded = load_confirmed_profile(
                '{"PIP-001": "Replacement", "AIF-005": "No", "AIF-005-DETAILS": "Invalid detail"}'
            )
        self.assertEqual(loaded, {"product": {"PIP-001": "Existing profile"}, "ai_function": {}})
