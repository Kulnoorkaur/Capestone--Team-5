"""Run from the checkout with: python test/live_gemini_chat_buddy.py

Live A–E use the configured Gemini API. F and G use deterministic fixtures. The headless
workflow executes production handlers, without testing Streamlit widgets.
"""
import argparse
import ast
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.chatbot import chat_llm as llm
from app.chatbot.questionnaire_bridge import (
    CONDITIONAL_FIELDS, QUESTIONNAIRE_FIELDS, QuestionnaireBridge,
)

PRODUCT = (
    "RetinaGuard AI, Version 1.0, supports diabetic retinopathy screening in adults aged 18 "
    "and older with type 1 or type 2 diabetes. Ophthalmologists, optometrists, and other "
    "trained healthcare professionals use it in outpatient ophthalmology, optometry, and "
    "diabetes screening clinics. The software analyzes digital color retinal fundus "
    "photographs uploaded through a clinical interface. It performs image quality checks, "
    "preprocessing, and CNN analysis to identify microaneurysms, hemorrhages, and exudates. "
    "It generates screening classifications, probability estimates, and alerts, delivered "
    "through a dashboard, reports, and notifications. It supports screening and prioritization "
    "but does not provide definitive diagnoses or independently initiate clinical actions. "
    "Healthcare professionals review original images and AI results before referral, "
    "diagnostic, or treatment decisions. Users require product-specific training. "
    "Poor-quality images are flagged or rejected."
)
HANDOFF = (
    "RetinaGuard AI accepts digital retinal fundus photographs uploaded by healthcare "
    "professionals. It uses a convolutional neural network to identify signs of diabetic "
    "retinopathy and generates screening labels, probability estimates, and alerts. Results "
    "appear on a clinical dashboard and in reports. The software does not independently "
    "initiate referrals or treatment decisions."
)
PLANNED = (
    "RetinaGuard AI currently generates screening labels and displays them on a clinical "
    "dashboard. Probability estimates and automated alerts are planned for a future version "
    "but are not available in Version 1.0. The software automatically processes uploaded "
    "images, but it cannot initiate referrals or other clinical actions without human approval."
)
FULL_INTAKE = (
    "Our product is RetinaGuard AI, Version 1.0. It is an AI-powered medical imaging "
    "software designed to help ophthalmologists, optometrists, and other trained healthcare "
    "professionals screen adults with diabetes for signs of diabetic retinopathy. "
    "The software analyzes digital color retinal fundus photographs to identify potential "
    "abnormalities. The imaging modality is retinal fundus photography."
)


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def workflow(questionnaire="D2.1"):
    # Load only definitions. Evaluating the Streamlit entry point would render
    # widgets and use the runtime session. Fail visibly if handler dependencies change.
    filename = ROOT / "app/chatbot/chat_app.py"
    tree = ast.parse(filename.read_text())
    constants = {"WELCOME", "QUESTIONNAIRES", "QUESTIONNAIRE_NAMES"}
    nodes = [
        n for n in tree.body if isinstance(n, ast.FunctionDef) or (
            isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in constants for t in n.targets
            )
        )
    ]
    state = State()
    env = {
        "st": SimpleNamespace(session_state=state),
        "QuestionnaireBridge": QuestionnaireBridge,
        "CONDITIONAL_FIELDS": CONDITIONAL_FIELDS,
        "extract_questionnaire_fields": llm.extract_questionnaire_fields,
        "generate_questionnaire_question": llm.generate_questionnaire_question,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(filename), "exec"), env)
    env["initialize_session"]()
    env["bridge"] = state.questionnaire_bridge
    state.active_questionnaire = questionnaire
    state.intake_started = True
    return state, env


def record_turn(state, message, source_id="1"):
    state.carryover["turns"][source_id] = {
        "message": message, "questionnaire": state.active_questionnaire, "question": None,
    }


def stage_parent(state, field, value, message, source_id="1"):
    record_turn(state, message, source_id)
    state.field_suggestions[field] = value
    state.carryover["evidence"][field] = {
        "source_id": source_id, "quote": message, "value": value,
    }


def check(condition, failure, failures):
    if not condition:
        failures.append(failure)


def test_a():
    result = llm.extract_questionnaire_fields(PRODUCT)
    # Explicit facts only. Other supported fields are allowed and printed for review.
    expected = {"PIP-001", "PIP-002", "PIP-003", "PIP-006", "PIP-007", "PIP-008",
                "PIP-009", "PIP-011", "PIP-012", "PIP-016", "PIP-017", "PIP-020",
                "PIP-021", "PIP-022", "PIP-023", "PIP-024"}
    missed = sorted(expected - result.keys())
    bridge = QuestionnaireBridge()
    valid = {f: bridge.validate_answer(f, v)[0] for f, v in result.items()}
    fixed = {"PIP-006": "Other", "PIP-008": "Healthcare professional only",
             "PIP-009": "Yes", "PIP-017": "Screening"}
    warnings = [f for f, v in fixed.items() if f in result and result[f] != v]
    warnings += sorted(result.keys() & {"PIP-013", "PIP-018"})
    failures = [f"Review potentially unsupported or inconsistent field {f}" for f in warnings]
    if not result or not all(valid.values()):
        failures.append("Expected valid multi-field candidates")
    if len(result.keys() & expected) < 2:
        failures.append("Fewer than two expected fields were extracted")
    name = str(result.get("PIP-001", "")).casefold()
    if "PIP-001" in result and ("retinaguard ai" not in name or "1.0" not in name):
        failures.append("Product name or version was missing or inconsistent")
    return {"candidates": result, "schema_valid": valid, "expected_but_missed": missed,
            "semantic_review": "Free text and unlisted facts require human review."}, failures


def test_conditional(questionnaire, parent, child, message, trigger, terms):
    state, env = workflow(questionnaire)
    failures = []
    bridge = state.questionnaire_bridge
    check(child not in bridge.get_active_conditional_fields(questionnaire),
          "Child eligible before parent confirmation", failures)
    proposed = llm.extract_questionnaire_fields(message, questionnaire=questionnaire,
                                                target_field_id=parent)
    check(child not in proposed, "Child proposed before parent confirmation", failures)
    check(proposed.get(parent) == trigger, f"Expected parent {parent} = {trigger}", failures)
    # Exercise the conditional independently if live parent extraction misses.
    stage_parent(state, parent, trigger, message)
    assert env["confirm_answer"](parent, trigger)[0]
    check(child in bridge.get_active_conditional_fields(questionnaire),
          "Confirmed trigger did not activate child", failures)
    env["process_next_question"]()
    value = state.field_suggestions.get(child)
    evidence = state.carryover["evidence"].get(child, {})
    if terms is None:
        check(value is None and not evidence, "Invented detail from the parent selection", failures)
        check(state.asked_field == child, "Questionnaire did not ask the missing follow-up", failures)
    else:
        check(isinstance(value, str) and all(t in value.casefold() for t in terms),
              f"Missing or inaccurate follow-up {child}", failures)
        check(bool(evidence.get("quote")) and evidence["quote"] in message and
              evidence.get("source_id") == "1" and all(t in evidence["quote"].casefold() for t in terms),
              "Missing or invalid source evidence", failures)
    check(child not in bridge.answers, "Follow-up was automatically confirmed", failures)
    if value is not None:
        env["reject_answer"](child)
        env["process_next_question"]()
        check(child not in state.field_suggestions, "Rejected suggestion reappeared", failures)
    return {"parent_extraction": proposed, "simulated_confirmation": trigger,
            "follow_up": value, "evidence": evidence}, failures


def test_c(explicit_roles=False):
    state, env = workflow()
    roles = " Ophthalmologists receive the AI results, and optometrists make the final clinical decision."
    record_turn(state, HANDOFF + roles if explicit_roles else HANDOFF)
    bridge = state.questionnaire_bridge
    # Seed valid D2.1 values to reach the real handoff without 24 Gemini calls.
    for field in QUESTIONNAIRE_FIELDS["D2.1"]:
        options = bridge.get_field_options(field)
        value = "No" if field == "PIP-009" else options[0] if options else "Fixture value"
        if bridge.get_field_type(field) == "multiselect":
            value = [value]
        assert bridge.save_answer(field, value)[0]
    env["schedule_next_question"]()
    env["process_next_question"]()
    candidates = dict(state.field_suggestions)
    failures = compare_options(candidates, {
        "AIF-001": ["Medical images"], "AIF-003": ["User upload"],
        "AIF-006": ["Label", "Probability", "Alert"],
        "AIF-007": ["Report", "Dashboard"], "AIF-019": "No",
    })
    processing = str(candidates.get("AIF-004", "")).lower()
    check("cnn" in processing or "convolutional" in processing, "Missing CNN analysis", failures)
    allowed = {"AIF-001", "AIF-003", "AIF-004", "AIF-006", "AIF-007", "AIF-008", "AIF-019"}
    if explicit_roles:
        allowed.add("AIF-011")
        value = candidates.get("AIF-011", "").casefold()
        quote = state.carryover["evidence"].get("AIF-011", {}).get("quote", "").casefold()
        check(all(role in value and role in quote for role in ("ophthalmologist", "optometrist")),
              "AIF-011 did not retain both explicit roles and their evidence", failures)
    unexpected = sorted(candidates.keys() - allowed)
    check(not unexpected, f"Unexpected fields without direct support: {unexpected}", failures)
    check(not (candidates.keys() & bridge.answers.keys()), "Carryover saved an answer", failures)
    check(state.carryover["handoff_done"], "Handoff did not run", failures)
    check(all(bridge.validate_answer(f, v)[0] for f, v in candidates.items()),
          "Handoff returned invalid field or option", failures)
    return {"candidates": candidates, "evidence": state.carryover["evidence"]}, failures


def compare_options(result, expected):
    failures = []
    for field, value in expected.items():
        actual = result.get(field)
        match = (isinstance(actual, list) and set(actual) == set(value)) if isinstance(value, list) else actual == value
        check(match, f"{field}: expected {value!r}, got {actual!r}", failures)
    return failures


def test_d():
    result = llm.extract_questionnaire_fields(PLANNED, questionnaire="D2.2")
    return result, compare_options(result, {
        "AIF-006": ["Label"], "AIF-007": ["Dashboard"], "AIF-019": "No",
    })


def test_e():
    results = {}
    failures = []
    for label, later in (
        ("unresolved", "Version 1.0 does not generate probability estimates."),
        ("correction", "Correction: my earlier statement was wrong. Version 1.0 generates screening labels only and does not generate probability estimates."),
    ):
        result = llm.extract_questionnaire_fields(
            None, questionnaire="D2.2", eligible_fields={"AIF-006": ["1", "2"]},
            source_turns={
                "1": {"message": "Version 1.0 generates probability estimates.", "original_question": ""},
                "2": {"message": later, "original_question": ""},
            },
        )
        results[label] = result
        if label == "unresolved":
            check("AIF-006" not in result, "Unresolved contradiction produced a candidate", failures)
        else:
            candidate = result.get("AIF-006", {})
            check(candidate.get("value") == ["Label"] and candidate.get("source_id") == "2",
                  "Explicit correction did not produce Label only with corrected evidence", failures)
    return results, failures


def test_f():
    state, env = workflow()
    bridge = state.questionnaire_bridge
    message = "The product outputs a score and uses a dashboard."
    record_turn(state, message)
    assert bridge.save_answer("AIF-007", ["Report"])[0]
    fields = {"AIF-006": ["1"], "AIF-007": ["1"], "AIF-020": ["1"],
              "AIF-003": ["1"], "AIF-004": ["1"], "AIF-999": ["1"]}
    candidate = {"value": ["Score"], "source_id": "1", "quote": "outputs a score"}
    payload = {
        "AIF-006": candidate, "AIF-007": {**candidate, "value": ["Dashboard"]},
        "AIF-020": {**candidate, "value": ["Invalid option"]},
        "AIF-003": {"value": ["PACS"], "source_id": "1"},
        "AIF-004": {**candidate, "value": "CNN", "quote": "fabricated"},
        "AIF-999": candidate,
    }
    with patch.object(llm, "get_gemini_client", return_value=object()):
        with patch.object(llm, "generate_content_with_retry", return_value=SimpleNamespace(text=json.dumps(payload))):
            assert env["open_carryover_review"]("D2.2", fields)
            assert state.field_suggestions == {"AIF-006": ["Score"]}
            assert bridge.answers["AIF-007"] == ["Report"]
            env["reject_answer"]("AIF-006")
            assert not env["open_carryover_review"]("D2.2", fields)
            assert not state.field_suggestions
        for failure in (None, RuntimeError("simulated API failure")):
            state, env = workflow()
            message = "We use retinal fundus photography."
            stage_parent(state, "PIP-006", "Other", message)
            assert env["confirm_answer"]("PIP-006", "Other")[0]
            stub = {"side_effect": failure} if failure else {"return_value": SimpleNamespace(text="")}
            with patch.object(llm, "generate_content_with_retry", **stub):
                with redirect_stdout(io.StringIO()):
                    env["process_next_question"]()
            assert state.asked_field == "PIP-006-OTHER" and not state.field_suggestions
    return {"invalid_candidates_filtered": True, "confirmed_value_preserved": True,
            "rejected_evidence_suppressed": True, "progression_after_empty_or_error": True}, []


def test_g():
    positive = "Version 1.0 generates probability estimates."
    negative = "Version 1.0 does not generate probability estimates."
    correction = (
        "Correction: my earlier statement was wrong. Version 1.0 generates screening labels "
        "only and does not generate probability estimates."
    )
    dashboard = "Results appear on a dashboard."
    no_autonomy = "The product cannot initiate referrals without human approval."
    # This is the actual response from the failed live regression.
    recorded = {"AIF-006": {"value": ["Probability"], "source_id": "1", "quote": positive}}
    unrelated = {
        "AIF-007": {"value": ["Dashboard"], "source_id": "2", "quote": dashboard},
        "AIF-019": {"value": "No", "source_id": "2", "quote": no_autonomy},
    }
    corrected = {"AIF-006": {
        "value": ["Label"], "source_id": "2", "quote": correction.split(". ", 1)[1],
    }}
    combined = "Version 1.0 generates screening labels and probability estimates."
    mixed = {"AIF-006": {
        "value": ["Label", "Probability"], "source_id": "1", "quote": combined,
    }}
    fixtures = (
        ("unresolved", positive, negative, recorded, {}),
        ("corrected", positive, correction, corrected, corrected),
        ("stale_after_correction", positive, correction, recorded, {}),
        ("denied_option_after_correction", positive, correction, {
            "AIF-006": {**corrected["AIF-006"], "value": ["Label", "Probability"]},
        }, {}),
        ("unrelated_and_negative", positive, f"{negative} {dashboard} {no_autonomy}",
         {**recorded, **unrelated}, unrelated),
        ("disputed_multiselect", combined, negative, mixed, {}),
        ("multi_sentence_quote", f"{positive} {dashboard}", negative, {
            "AIF-006": {**recorded["AIF-006"], "quote": f"{positive} {dashboard}"},
        }, {}),
        ("different_version", positive, negative.replace("1.0", "2.0"), recorded, recorded),
        ("ineligible_contradiction", positive, negative, recorded, recorded),
        ("invalid_quote", positive, negative, {
            "AIF-006": {**recorded["AIF-006"], "quote": "Fabricated quote"},
        }, {}),
        ("invalid_option", positive, negative.replace("1.0", "2.0"), {
            "AIF-006": {**recorded["AIF-006"], "value": ["Unsupported option"]},
        }, {}),
    )
    results = {}
    with patch.object(llm, "get_gemini_client", return_value=object()):
        for name, first, second, response, expected in fixtures:
            source_turns = {
                turn_id: {"message": message, "original_question": ""}
                for turn_id, message in (("1", first), ("2", second))
            }
            eligible = {field: ["1", "2"] for field in response}
            if name == "ineligible_contradiction":
                eligible["AIF-006"] = ["1"]
            with patch.object(llm, "generate_content_with_retry", return_value=SimpleNamespace(text=json.dumps(response))):
                actual = llm.extract_questionnaire_fields(
                    None, questionnaire="D2.2", source_turns=source_turns,
                    eligible_fields=eligible,
                )
            assert actual == expected, (name, actual, expected)
            results[name] = "PASS"

        ordinary = {"AIF-006": ["Probability"]}
        with patch.object(llm, "generate_content_with_retry", return_value=SimpleNamespace(text=json.dumps(ordinary))):
            assert llm.extract_questionnaire_fields(
                f"{positive} {negative}", questionnaire="D2.2",
            ) == ordinary
        results["ordinary_extraction_unchanged"] = "PASS"

        state, env = workflow("D2.2")
        record_turn(state, positive)
        record_turn(state, f"{negative} {dashboard} {no_autonomy}", source_id="2")
        field_sources = dict.fromkeys({**recorded, **unrelated}, ["1", "2"])
        with patch.object(llm, "generate_content_with_retry", return_value=SimpleNamespace(
            text=json.dumps({**recorded, **unrelated})
        )):
            assert env["open_carryover_review"]("D2.2", field_sources, handoff=True)
        assert state.field_suggestions == {"AIF-007": ["Dashboard"], "AIF-019": "No"}
        assert not state.questionnaire_bridge.answers
        assert env["confirm_answer"]("AIF-019", "No")[0]
        assert state.questionnaire_bridge.answers == {"AIF-019": "No"}
        assert state.field_suggestions == {"AIF-007": ["Dashboard"]}
        results["explicit_confirmation_required"] = "PASS"
    return results, []


class Meter:
    def __init__(self, original, max_calls=16):
        self.original = original
        self.max_calls = max_calls
        self.calls = 0
        self.tokens = 0
        self.responses_with_usage = 0

    def client(self):
        client = self.original()

        def generate(**kwargs):
            if self.calls >= self.max_calls:
                raise RuntimeError("Live API call budget exhausted")
            self.calls += 1
            response = client.models.generate_content(**kwargs)
            usage = getattr(response, "usage_metadata", None)
            total = getattr(usage, "total_token_count", None)
            if total is not None:
                self.responses_with_usage += 1
                self.tokens += total
            return response

        return SimpleNamespace(models=SimpleNamespace(generate_content=generate))


def main():
    cases = [
        ("A", "live extraction", "Multiple supported D2.1 values", test_a),
        ("A2", "live + headless workflow", "Exact full intake supplies the modality follow-up",
         lambda: test_conditional("D2.1", "PIP-006", "PIP-006-OTHER",
             FULL_INTAKE, "Other", ("retinal", "fundus"))),
        ("B1", "live + headless workflow", "Other activates imaging modality detail",
         lambda: test_conditional("D2.1", "PIP-006", "PIP-006-OTHER",
             "Our software uses digital color retinal fundus photography to screen adults with diabetes.",
             "Other", ("digital", "fundus"))),
        ("B2", "live + headless workflow", "Review trigger activates professional review detail",
         lambda: test_conditional("D2.2", "AIF-016", "AIF-016-DETAILS",
             "A healthcare professional always reviews the original images and AI results before making referral, diagnostic, or treatment decisions.",
             "Always", ("review",))),
        ("C", "live + headless workflow", "D2.1 evidence proposes six D2.2 answers", test_c),
        ("C2", "live + headless workflow", "Explicit roles also produce an evidence-backed AIF-011",
         lambda: test_c(explicit_roles=True)),
        ("D", "live extraction", "Current capabilities exclude future features", test_d),
        ("D2", "live + headless workflow", "Parent selection alone does not supply follow-up detail",
         lambda: test_conditional("D2.1", "PIP-006", "PIP-006-OTHER",
             "For our imaging modality, please select Other.", "Other", None)),
        ("E", "live extraction", "Omit unresolved conflicts and recognize explicit corrections", test_e),
        ("F", "mocked failure + headless workflow", "Filter malformed candidates and continue", test_f),
        ("G", "mocked contradiction + headless workflow", "Withhold direct conflicts and preserve valid candidates", test_g),
    ]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", choices=[case[0] for case in cases],
                        help="Run a specific case. Repeat to run multiple cases.")
    parser.add_argument("--max-calls", type=int, default=16,
                        help="Maximum number of live Gemini calls (default: 16).")
    args = parser.parse_args()
    if args.max_calls < 1:
        parser.error("--max-calls must be positive")
    selected = args.case
    if selected:
        by_name = {case[0]: case for case in cases}
        cases = [by_name[name] for name in selected]
    meter = Meter(llm.get_gemini_client, max_calls=args.max_calls)
    statuses = []
    key_configured = bool(os.getenv("GEMINI_API_KEY"))
    for name, mode, expected, test in cases:
        start, tokens = meter.calls, meter.tokens
        if name not in {"F", "G"} and not key_configured:
            status, actual, failures = "SKIP", None, ["GEMINI_API_KEY is unavailable"]
        else:
            try:
                with patch.object(llm, "get_gemini_client", meter.client), redirect_stdout(io.StringIO()):
                    actual, failures = test()
                status = "FAIL" if failures else "PASS"
            except Exception as error:
                status, actual = "FAIL", None
                # SDK exception text can include request details. Report type/status only.
                code = getattr(error, "code", None)
                failures = [type(error).__name__ + (f" (status {code})" if isinstance(code, int) else "")]
        statuses.append(status)
        print(json.dumps({"test": name, "mode": mode, "expected": expected, "actual": actual,
                          "status": status, "failures": failures, "live_calls": meter.calls - start,
                          "reported_tokens": meter.tokens - tokens}, ensure_ascii=False), flush=True)
    print(json.dumps({"total_live_calls": meter.calls, "reported_total_tokens": meter.tokens,
                      "responses_with_usage": meter.responses_with_usage,
                      "limits": "Workflow handlers only, no Streamlit UI. Semantic assertions cover selected facts."}))
    return int(any(s != "PASS" for s in statuses))


if __name__ == "__main__":
    raise SystemExit(main())
