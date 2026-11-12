import sys
from pathlib import Path

QDIR = Path(__file__).resolve().parents[1] / "app" / "deliverable_2" / "questionnaires"
sys.path.insert(0, str(QDIR))

from algorithm_change_control import (FIELDS, LOCKED, SITE, ADAPTIVE, FRAMEWORKS, build_record, validate,
                                      evaluate, is_active, MANUAL_REVIEW, STATUS_INCOMPLETE, STATUS_READY)

EV = "Design spec v2.1, s.3"


def ans(value, details="", evidence=EV):
    return {"value": value, "details": details, "evidence": evidence}


def locked_no_changes():
    """Scenario A: locked model, no planned changes, everything documented."""
    a = {
        "ACC-001": ans("LungNodule-AI v2.1"), "ACC-002": ans("AIF-004, AIF-006"),
        "ACC-003": ans(["Supervised"]), "ACC-004": ans(["CNN"]),
        "ACC-005": ans("No"), "ACC-006": ans("Yes"), "ACC-007": ans("Fixed"),
        "ACC-008": ans(LOCKED), "ACC-009": ans(["None"]), "ACC-012": ans("No"),
        "ACC-013": ans("No"),
        "ACC-021": ans("Yes", "SOP-CC-004 v3"), "ACC-022": ans("Per SOP-CC-004 s.5"),
        "ACC-023": ans("Regression suite + subgroup checks"), "ACC-024": ans("Yes", "Per SOP"),
        "ACC-025": ans("Yes", "Release registry"), "ACC-026": ans(["Installed by manufacturer"]),
        "ACC-027": ans(["Release notes"]), "ACC-028": ans(["Performance monitoring"]),
        "ACC-029": ans("Not applicable (not previously released)", "First release"),
    }
    return a


def adaptive():
    """Scenario B: continuously adaptive, planned changes, documented plan."""
    a = locked_no_changes()
    a.update({
        "ACC-008": ans(ADAPTIVE), "ACC-009": ans(["Model weights"]),
        "ACC-010": ans("Monthly local fine-tuning; QA lead approves"),
        "ACC-011": ans(["Performance gate before activation", "Automatic rollback"]),
        "ACC-012": ans("Yes", "Radiologist corrections, screened"),
        "ACC-013": ans("Yes"), "ACC-014": ans(["Retraining on additional data of the same kind"]),
        "ACC-015": ans("Scheduled"), "ACC-016": ans("Retrain within +/-2% sensitivity bound"),
        "ACC-017": ans("No"), "ACC-018": ans("No"),
        "ACC-019": ans("Yes", "PCCP-001 v1"),
        "ACC-020": ans({fw: "Planned for submission" for fw in FRAMEWORKS}),
    })
    return a


def ids(flags):
    return {f["flag_id"] for f in flags}


def test_locked_complete_is_ready_not_go():
    rec = build_record("A", locked_no_changes())
    assert rec["validation_problems"] == []
    assert rec["profile_status"] == STATUS_READY
    assert "Go" not in rec["profile_status"].split(":")[0]


def test_conditional_fields_become_not_applicable():
    rec = build_record("A", locked_no_changes())
    for fid in ("ACC-010", "ACC-011", "ACC-014", "ACC-016", "ACC-019", "ACC-020"):
        assert fid in rec["not_applicable"] and fid not in rec["answers"]


def test_adaptive_documented_is_ready():
    rec = build_record("B", adaptive())
    assert rec["validation_problems"] == []
    assert rec["profile_status"] == STATUS_READY


def test_missing_behaviour_forces_manual_review():
    a = locked_no_changes(); del a["ACC-008"]
    rec = build_record("x", a)
    assert rec["profile_status"] == MANUAL_REVIEW and "FLG-01" in ids(rec["flags"])


def test_unknown_behaviour_forces_manual_review():
    a = locked_no_changes(); a["ACC-008"] = ans("Unknown", "Developer has not said")
    assert build_record("x", a)["profile_status"] == MANUAL_REVIEW


def test_locked_conflict_with_feedback_and_configurable_thresholds():
    a = locked_no_changes()
    a["ACC-012"] = ans("Yes", "site corrections reused")
    a["ACC-007"] = ans("Configurable by site or user")
    rec = build_record("x", a)
    f = [x for x in rec["flags"] if x["flag_id"] == "FLG-02"][0]
    assert {"ACC-012", "ACC-007"} <= set(f["fields"]) and rec["profile_status"] == MANUAL_REVIEW


def test_adaptive_without_safeguards_is_blocking():
    a = adaptive(); a["ACC-011"] = ans(["None"]); 
    rec = build_record("x", a)
    assert "FLG-03" in ids(rec["flags"]) and rec["profile_status"] == MANUAL_REVIEW


def test_adaptive_without_monitoring_is_blocking():
    a = adaptive(); a["ACC-028"] = ans(["None"])
    assert "FLG-03" in ids(build_record("x", a)["flags"])


def test_planned_changes_without_change_plan_is_gap_not_pass():
    a = adaptive(); a["ACC-019"] = ans("No")
    rec = build_record("x", a)
    assert "FLG-04" in ids(rec["flags"]) and rec["profile_status"] != STATUS_READY
    assert "ACC-020" in rec["not_applicable"]  # status question not triggered when no plan


def test_change_altering_intended_use_is_blocking():
    a = adaptive(); a["ACC-017"] = ans("Yes", "adds paediatric use: PIP-011")
    assert build_record("x", a)["profile_status"] == MANUAL_REVIEW


def test_authorized_plan_without_document_is_unverified():
    a = adaptive()
    a["ACC-019"] = ans("Yes", "")  # triggers details-required too
    a["ACC-020"] = ans({**{fw: "Planned for submission" for fw in FRAMEWORKS}, "FDA": "Authorized or accepted"}, evidence="")
    rec = build_record("x", a)
    assert "FLG-06" in ids(rec["flags"])


def test_unknown_requires_explanation():
    a = locked_no_changes(); a["ACC-005"] = ans("Unknown", "")
    assert any(p["id"] == "ACC-005" for p in validate(a))


def test_none_cannot_combine_with_other_selection():
    a = locked_no_changes(); a["ACC-009"] = ans(["None", "Calibration"])
    assert any(p["id"] == "ACC-009" and "cannot be combined" in p["problem"] for p in validate(a))


def test_missing_required_is_reported_and_status_incomplete():
    a = locked_no_changes(); del a["ACC-022"]
    rec = build_record("x", a)
    assert any(p["id"] == "ACC-022" for p in rec["validation_problems"])
    assert rec["profile_status"] == STATUS_INCOMPLETE


def test_missing_evidence_is_documentation_gap():
    a = locked_no_changes(); a["ACC-023"] = ans("Regression suite", evidence="")
    rec = build_record("x", a)
    f = [x for x in rec["flags"] if x["flag_id"] == "FLG-10"][0]
    assert "ACC-023" in f["fields"] and rec["profile_status"] == STATUS_INCOMPLETE


def test_aif_reference_pattern_enforced():
    a = locked_no_changes(); a["ACC-002"] = ans("the main function")
    assert any(p["id"] == "ACC-002" for p in validate(a))


def test_schema_has_29_unique_fields_and_valid_conditions():
    idl = [f["id"] for f in FIELDS]
    assert len(idl) == 29 == len(set(idl))
    for f in FIELDS:
        if f["when"]:
            parent = f["when"]["field"]
            assert parent in idl and idl.index(parent) < idl.index(f["id"])
            for v in f["when"]["in"]:
                assert v in next(x for x in FIELDS if x["id"] == parent)["options"]


def test_app_loads_and_flags_missing_behaviour():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(QDIR / "algorithm_change_control_app.py"), default_timeout=30).run()
    assert not at.exception
    assert "manual regulatory review required" in " ".join(e.value for e in at.error)
