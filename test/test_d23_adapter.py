import unittest

from app.chatbot.d23_adapter import D23AnswerAdapter
from app.deliverable_2.questionnaires.algorithm_change_control import (
    ADAPTIVE,
    FIELDS,
    FRAMEWORKS,
    LOCKED,
    SITE,
    build_record,
)


class D23AnswerAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = D23AnswerAdapter()
        self.algorithm = self.adapter.add_algorithm("Demo model", "1.0")

    def save(self, field_id, value, **metadata):
        self.adapter.save_answer(self.algorithm, field_id, value, **metadata)

    def snapshot(self):
        return self.adapter.get_algorithm(self.algorithm)

    def record(self):
        return self.adapter.build_record(self.algorithm)

    def activate_framework_status(self):
        self.save("ACC-013", "Yes")
        self.save("ACC-019", "Yes", details="Change plan CP-01")

    def test_all_29_fields_and_native_record_format(self):
        overrides = {
            "ACC-002": "AIF-004, AIF-006",
            "ACC-008": ADAPTIVE,
            "ACC-013": "Yes",
            "ACC-019": "Yes",
        }
        expected = {}
        for definition in FIELDS:
            field_id = definition["id"]
            options = definition["options"]
            field_type = definition["type"]
            if field_type in ("text", "longtext"):
                value = f"Description for {field_id}"
            elif field_type == "multiselect":
                value = options[:1]
            elif field_type == "perframework":
                value = dict.fromkeys(FRAMEWORKS, "Not submitted")
            else:
                value = options[0]
            value = overrides.get(field_id, value)
            self.save(field_id, value, details="Reviewed explanation", evidence="CP-01 v1, §2")
            expected[field_id] = {
                "value": value, "details": "Reviewed explanation", "evidence": "CP-01 v1, §2",
            }
        self.assertEqual(len(expected), 29)
        self.assertEqual(self.adapter.algorithm_ids, (self.algorithm,))
        self.assertEqual(self.record(), build_record("Demo model — 1.0", expected))
        self.assertEqual(self.record()["validation_problems"], [])

    def test_distinct_algorithm_records_and_stable_identity(self):
        second = self.adapter.add_algorithm("Demo model", "1.0")
        self.assertNotEqual(self.algorithm, second)
        self.save("ACC-008", LOCKED)
        self.adapter.save_answer(second, "ACC-008", ADAPTIVE)
        self.adapter.update_identity(self.algorithm, "Renamed model", "1.1")
        self.assertEqual(self.adapter.algorithm_ids, (self.algorithm, second))
        self.assertEqual(self.snapshot()["name"], "Renamed model")
        self.assertEqual(self.snapshot()["version"], "1.1")
        self.assertEqual(self.snapshot()["answers"]["ACC-008"]["value"], LOCKED)
        self.assertEqual(self.adapter.get_algorithm(second)["answers"]["ACC-008"]["value"], ADAPTIVE)
        self.assertIn("ACC-010", self.adapter.active_field_ids(second))
        self.assertNotIn("ACC-010", self.adapter.active_field_ids(self.algorithm))

    def test_partial_record_does_not_confirm_identity_as_an_answer(self):
        self.assertEqual(self.snapshot()["answers"], {})
        self.assertEqual(len(self.adapter.active_field_ids(self.algorithm)), 20)
        self.assertIsNone(self.record()["answers"]["ACC-001"]["value"])
        self.assertEqual(len(self.record()["not_applicable"]), 9)
        self.assertTrue(any(issue["id"] == "ACC-001" for issue in self.record()["validation_problems"]))
        self.assertIn("FLG-01", {flag["flag_id"] for flag in self.record()["flags"]})

    def test_recursive_activation_and_parent_changes_prune_descendants(self):
        self.save("ACC-013", "Unknown")
        self.assertIn("ACC-014", self.adapter.active_field_ids(self.algorithm))
        for field_id, value in (("ACC-019", "Yes"), ("ACC-020", {"FDA": "Not submitted"})):
            with self.subTest(field_id=field_id), self.assertRaisesRegex(ValueError, "inactive"):
                self.save(field_id, value)

        self.activate_framework_status()
        self.save("ACC-020", {"FDA": "Not submitted"}, source_quote="We have not submitted the plan.")
        self.assertIn("ACC-020", self.adapter.active_field_ids(self.algorithm))
        self.save("ACC-013", "Unknown", details="Future plans are unresolved.")
        self.assertNotIn("ACC-019", self.snapshot()["answers"])
        self.assertNotIn("ACC-020", self.snapshot()["answers"])
        self.assertNotIn("ACC-020", self.snapshot()["source_quotes"])
        self.assertNotIn("ACC-020", self.adapter.active_field_ids(self.algorithm))

        self.activate_framework_status()
        self.assertNotIn("ACC-020", self.snapshot()["answers"])
        self.assertIsNone(self.record()["answers"]["ACC-020"]["value"])

    def test_parent_edit_and_removal_preserve_still_active_fields(self):
        self.save("ACC-008", ADAPTIVE, evidence="Design §3", source_quote="The model learns in the field.")
        self.save("ACC-010", "Update after review", evidence="Design §4", source_quote="Update after review")
        self.save("ACC-011", ["Human approval"], evidence="Design §5", source_quote="A human approves.")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "ACC-008: Expected an allowed option"):
            self.save("ACC-008", "Unsupported behavior", source_quote="Unconfirmed replacement")
        self.assertEqual(self.snapshot(), before)

        self.save("ACC-008", SITE)
        after = self.snapshot()
        self.assertEqual(after["answers"], {
            "ACC-008": {"value": SITE, "details": "", "evidence": ""},
            "ACC-011": before["answers"]["ACC-011"],
        })
        self.assertEqual(after["source_quotes"], {"ACC-011": before["source_quotes"]["ACC-011"]})
        self.adapter.remove_answer(self.algorithm, "ACC-008")
        self.assertNotIn("ACC-011", self.snapshot()["answers"])

    def test_missing_explanation_and_document_reference_are_owner_findings(self):
        self.save("ACC-005", "Yes", source_quote="We use a third-party component.")
        record = self.record()
        self.assertTrue(any(
            problem["id"] == "ACC-005" and problem["problem"].startswith("Explanation required")
            for problem in record["validation_problems"]
        ))
        self.assertTrue(any(
            flag["flag_id"] == "FLG-10" and "ACC-005" in flag["fields"] for flag in record["flags"]
        ))
        self.assertEqual(record["answers"]["ACC-005"]["evidence"], "")
        self.assertNotIn("source_quotes", record)
        self.save("ACC-005", "Yes", details="Component and role", evidence="SBOM v1, §3",
                  source_quote="We use a third-party component.")
        record = self.record()
        self.assertFalse(any(problem["id"] == "ACC-005" for problem in record["validation_problems"]))
        self.assertFalse(any(flag["flag_id"] == "FLG-10" for flag in record["flags"]))
        self.assertEqual(record["answers"]["ACC-005"]["evidence"], "SBOM v1, §3")
        self.assertEqual(self.snapshot()["source_quotes"]["ACC-005"], "We use a third-party component.")
        self.save("ACC-005", "No")
        self.assertEqual(self.snapshot()["answers"]["ACC-005"], {"value": "No", "details": "", "evidence": ""})
        self.assertNotIn("ACC-005", self.snapshot()["source_quotes"])

    def test_invalid_values_and_multiselect_conflicts_leave_previous_answers_intact(self):
        self.save("ACC-009", ["Model weights"], evidence="Design §3")
        original = self.snapshot()
        cases = (
            ("ACC-999", "Yes", "Unknown D2.3 field"),
            ("ACC-001", [], "non-empty text"),
            ("ACC-008", "Unsupported behavior", "allowed option"),
            ("ACC-009", "Model weights", "list of allowed options"),
            ("ACC-009", ["Unsupported option"], "list of allowed options"),
            ("ACC-009", ["None", "Model weights"], "cannot be combined"),
            ("ACC-009", ["Unknown", "Model weights"], "cannot be combined"),
            ("ACC-002", "No valid reference", "Expected a reference"),
        )
        for field_id, value, error in cases:
            with self.subTest(field_id=field_id, value=value):
                with self.assertRaisesRegex(ValueError, error):
                    self.save(field_id, value)
                self.assertEqual(self.snapshot(), original)
        self.save("ACC-002", "AIF-004 and AIF-006")
        self.assertEqual(self.snapshot()["answers"]["ACC-002"]["value"], "AIF-004 and AIF-006")

    def test_framework_maps_validate_statuses_but_allow_partial_values(self):
        self.activate_framework_status()
        partial = {"FDA": "Under review", "Health Canada": None}
        self.save("ACC-020", partial)
        self.assertEqual(self.record()["answers"]["ACC-020"]["value"], partial)
        self.assertIn(
            {"id": "ACC-020", "problem": "Required answer missing"},
            self.record()["validation_problems"],
        )
        for value, error in (
            ("Under review", "dictionary"),
            ({"Other framework": "Under review"}, "Unknown framework"),
            ({"FDA": "Approved"}, "Invalid status"),
        ):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, error):
                self.save("ACC-020", value)
        self.assertEqual(self.snapshot()["answers"]["ACC-020"]["value"], partial)

    def test_mutable_inputs_and_return_values_are_detached(self):
        value = ["CNN"]
        self.save("ACC-004", value)
        value.append("Hybrid")
        self.snapshot()["answers"]["ACC-004"]["value"].clear()
        self.record()["answers"]["ACC-004"]["value"].clear()
        self.assertEqual(self.snapshot()["answers"]["ACC-004"]["value"], ["CNN"])
