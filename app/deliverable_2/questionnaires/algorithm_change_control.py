"""Deliverable 2.3: algorithm and change-control questionnaire (schema + validation logic).

Single self-contained module. No imports from other team modules.
- SCHEMA section: the 29 fields (ACC-001..ACC-029). Edit here to change the questionnaire.
- LOGIC section: conditional visibility, validation, and the D2.3 Section 5 flag rules.
The questionnaire never produces a Go outcome; D1.6 requirement IDs are not stored here until verified.
"""
import re

# =====================================================================
# SCHEMA
# =====================================================================
UNKNOWN = "Unknown"
YNU = ["Yes", "No", UNKNOWN]
YPNU = ["Yes", "Partly", "No", UNKNOWN]
FRAMEWORKS = ["Health Canada", "FDA", "EU MDR", "EU AI Act"]
FRAMEWORK_STATUS = [
    "Not submitted", "Planned for submission", "Under review",
    "Authorized or accepted", "Not applicable (give rationale)", UNKNOWN,
]

LOCKED = "Locked (nothing changes in the field; any change is a new released version)"
SITE = "Site-specific configuration only"
ADAPTIVE = "Adaptive (changes in the field through learning)"


def field(fid, group, label, ftype, options=None, required=True, when=None,
          detail_on=None, gates="", pattern=None, help=None):
    """Build a field definition.

    ftype: text | longtext | select | multiselect | perframework
    when: {"field": "ACC-008", "in": [...]} -> field is conditional
    detail_on: values that require an explanation (Unknown always does)
    """
    return {
        "id": fid, "group": group, "label": label, "type": ftype,
        "options": options or [], "required": required, "when": when,
        "detail_on": detail_on or [], "gates": gates, "pattern": pattern,
        "help": help,
    }


G1 = "Algorithm identification and model characteristics"
G2 = "Locked or adaptive behaviour"
G3 = "Planned retraining and updates"
G4 = "Change management and verification"

FIELDS = [
    # ---- 2.1 ----
    field("ACC-001", G1, "Name and version identifier of the algorithm/model release (if different from the product version in PIP-001)", "text", gates="G1; G8"),
    field("ACC-002", G1, "Which AI function(s) from Deliverable 2.2 does this algorithm implement? (list AIF record references, e.g. AIF-004, AIF-006)", "text", pattern=r"AIF-\d{3}", gates="G1; G8"),
    field("ACC-003", G1, "Learning approach or technique", "multiselect",
          ["Supervised", "Semi-/self-supervised", "Unsupervised", "Reinforcement",
           "Rule-based or classical image processing (no learning)",
           "Fine-tuned pre-trained/foundation model", "Generative", "Other (describe)"],
          detail_on=["Other (describe)"], gates="G1/G2; G8"),
    field("ACC-004", G1, "Model architecture family (one model or several?)", "multiselect",
          ["CNN", "Vision transformer", "U-Net/segmentation", "Ensemble/multi-stage",
           "Classical machine learning", "Hybrid", "Other (describe)", UNKNOWN],
          detail_on=["Other (describe)"], gates="G5; G8"),
    field("ACC-005", G1, "Does the algorithm include third-party, pre-trained, or open-source components? (if Yes: component, supplier, version, role)", "select", YNU, detail_on=["Yes"], gates="G4; G5; G8"),
    field("ACC-006", G1, "For the same input and software version, is the output reproducible? (if No: source of variability)", "select", YNU, detail_on=["No"], gates="G5; G8"),
    field("ACC-007", G1, "Are thresholds, operating points, or calibration fixed, or changeable after release? (see AIF-009)", "select",
          ["Fixed", "Changed only by manufacturer release", "Configurable by site or user",
           "Adjusted automatically", UNKNOWN], gates="G5; G8"),
    # ---- 2.2 ----
    field("ACC-008", G2, "How does the algorithm behave after release into clinical use?", "select",
          [LOCKED, SITE, ADAPTIVE, UNKNOWN], gates="G2; G4; G5; G8"),
    field("ACC-009", G2, "Which elements can change without a new manufacturer release?", "multiselect",
          ["Model weights", "Thresholds/operating point", "Pre-/post-processing", "Calibration",
           "Input handling", "None", "Other (describe)", UNKNOWN],
          detail_on=["Other (describe)"], gates="G4; G8"),
    field("ACC-010", G2, "Adaptive mechanism: what triggers learning, what data is used, and who/what approves a change before it takes effect?", "longtext",
          when={"field": "ACC-008", "in": [ADAPTIVE]}, gates="G3; G8"),
    field("ACC-011", G2, "Safeguards on adaptive or site-configurable behaviour", "multiselect",
          ["Limits on size of change", "Performance gate before activation", "Human approval",
           "Automatic rollback", "Audit log", "None", "Other (describe)", UNKNOWN],
          when={"field": "ACC-008", "in": [SITE, ADAPTIVE]},
          detail_on=["Other (describe)"], gates="G4; G8; G10"),
    field("ACC-012", G2, "Can user corrections, site data, or clinical outcomes be fed back into training or tuning? (if Yes: data path and screening)", "select", YNU, detail_on=["Yes"], gates="G3; G4; G8"),
    # ---- 2.3 ----
    field("ACC-013", G3, "Are retraining, model updates, or other algorithm changes planned or anticipated during the lifecycle?", "select", YNU, gates="G8"),
    field("ACC-014", G3, "Which types of change are planned?", "multiselect",
          ["Retraining on additional data of the same kind", "Expanded or new training data",
           "Architecture change", "Threshold/operating-point change",
           "New scanners, vendors, or protocols", "Wider patient population",
           "New indication or intended use", "New output type", "Performance improvement",
           "Bug fix", "Cybersecurity patch", "Other (describe)"],
          when={"field": "ACC-013", "in": ["Yes", UNKNOWN]}, detail_on=["Other (describe)"], gates="G2; G8"),
    field("ACC-015", G3, "How often are changes expected, and what triggers them?", "select",
          ["Scheduled", "Performance-triggered", "Event-driven", "Ad hoc", UNKNOWN],
          when={"field": "ACC-013", "in": ["Yes", UNKNOWN]}, gates="G8; G10"),
    field("ACC-016", G3, "Describe each planned modification: what will change, the limits, and the expected effect on performance (one entry per modification)", "longtext",
          when={"field": "ACC-013", "in": ["Yes"]}, gates="G8; G9"),
    field("ACC-017", G3, "Would any planned change alter the intended use, indications, users, population, inputs, outputs, or performance claims recorded in D2.1/D2.2? (list affected PIP/AIF IDs)", "select",
          ["Yes", "No", "Sometimes", UNKNOWN],
          when={"field": "ACC-013", "in": ["Yes", UNKNOWN]}, detail_on=["Yes", "Sometimes"], gates="G1; G2; G8"),
    field("ACC-018", G3, "Will retraining use data that differs from the original in source, site, device vendor, or population? (if Yes: reference the D2.4 dataset record)", "select", YNU,
          when={"field": "ACC-013", "in": ["Yes"]}, detail_on=["Yes"], gates="G3; G8"),
    field("ACC-019", G3, "Is there a documented plan that pre-specifies the planned modifications and how each is verified (PCCP or equivalent)? (give document and framework)", "select", YPNU,
          when={"field": "ACC-013", "in": ["Yes"]}, detail_on=["Yes", "Partly"], gates="G8; G9"),
    field("ACC-020", G3, "Regulatory status of the change plan in each framework", "perframework", FRAMEWORK_STATUS,
          when={"field": "ACC-019", "in": ["Yes", "Partly", UNKNOWN]}, detail_on=["Not applicable (give rationale)"], gates="G8; G9"),
    # ---- 2.4 ----
    field("ACC-021", G4, "Is there a documented procedure for controlling software and algorithm changes within the QMS? (procedure ID and version)", "select", YPNU, detail_on=["Yes", "Partly"], gates="G8; G9"),
    field("ACC-022", G4, "How is each change assessed for regulatory significance? (criteria, who decides, how recorded)", "longtext", gates="G2; G8"),
    field("ACC-023", G4, "What verification and validation is performed before a change is released? (test data, regression testing, subgroup checks)", "longtext", gates="G5; G8"),
    field("ACC-024", G4, "Are acceptance criteria for releasing a change defined in advance? (describe)", "select", YPNU, detail_on=["Yes", "Partly"], gates="G5; G8"),
    field("ACC-025", G4, "Can the exact algorithm version, training-data version, and configuration behind any output be identified? (describe how)", "select", YPNU, detail_on=["Yes", "Partly"], gates="G8; G10"),
    field("ACC-026", G4, "How are updates delivered to deployed installations?", "multiselect",
          ["Automatic remote update", "Remote update with site/user approval", "Installed by manufacturer",
           "Installed by user", "Cloud-side change with no user action", "Other (describe)", UNKNOWN],
          detail_on=["Other (describe)"], gates="G7; G8"),
    field("ACC-027", G4, "How are users informed when the algorithm changes?", "multiselect",
          ["Release notes", "Labeling/IFU update", "In-product notice", "User training",
           "Notice of performance change", "None", UNKNOWN], gates="G7; G8"),
    field("ACC-028", G4, "How is performance monitored after an update, and can a previous version be restored?", "multiselect",
          ["Performance monitoring", "Drift detection", "User feedback channel",
           "Rollback to prior version", "None", "Other (describe)", UNKNOWN],
          detail_on=["Other (describe)"], gates="G8; G10"),
    field("ACC-029", G4, "Changes made since the last regulatory authorization or first release", "select",
          ["Changes have been made since last release", "None", "Not applicable (not previously released)"],
          detail_on=["Changes have been made since last release", "Not applicable (not previously released)"],
          help="For changes, list: version; date; description; regulatory assessment; outcome.", gates="G8; G9"),
]

BY_ID = {f["id"]: f for f in FIELDS}
GROUPS = [G1, G2, G3, G4]


# =====================================================================
# LOGIC
# =====================================================================

MANUAL_REVIEW = "manual regulatory review required"
STATUS_INCOMPLETE = "Incomplete: gaps recorded; no favourable outcome can be assigned"
STATUS_READY = ("Profile complete: pass to D2.6 decision logic "
                "(this is not a Go outcome and not a compliance finding)")


# ---------- helpers ----------
def _val(answers, fid):
    return (answers.get(fid) or {}).get("value")


def _selected(value):
    """Return a list of selected strings for any answer type."""
    if value is None:
        return []
    if isinstance(value, dict):
        return [v for v in value.values() if v]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value] if str(value).strip() else []


def is_blank(ftype, value):
    if ftype in ("text", "longtext"):
        return not (value or "").strip()
    if ftype == "select":
        return not value
    if ftype == "multiselect":
        return not value
    if ftype == "perframework":
        return not isinstance(value, dict) or any(not value.get(f) for f in FRAMEWORKS)
    return value is None


def is_active(fid, answers):
    """A conditional field is active only when its trigger field is active and matches."""
    f = BY_ID[fid]
    cond = f["when"]
    if not cond:
        return True
    parent = cond["field"]
    if not is_active(parent, answers):
        return False
    return any(v in cond["in"] for v in _selected(_val(answers, parent)))


def needs_details(fid, value):
    f = BY_ID[fid]
    sel = _selected(value)
    return UNKNOWN in sel or any(v in f["detail_on"] for v in sel)


# ---------- validation ----------
def validate(answers):
    """Return a list of {id, problem} for missing or malformed required answers."""
    problems = []
    for f in FIELDS:
        fid = f["id"]
        if not is_active(fid, answers) or not f["required"]:
            continue
        a = answers.get(fid) or {}
        value = a.get("value")
        if is_blank(f["type"], value):
            problems.append({"id": fid, "problem": "Required answer missing"})
            continue
        if f["pattern"] and not re.search(f["pattern"], value or ""):
            problems.append({"id": fid, "problem": f"Expected a reference matching {f['pattern']}"})
        if needs_details(fid, value) and not (a.get("details") or "").strip():
            problems.append({"id": fid, "problem": "Explanation required (Unknown, Other, or detail-triggering answer)"})
        sel = _selected(value) if f["type"] == "multiselect" else []
        exclusive = [v for v in sel if v in ("None", UNKNOWN)]
        if exclusive and len(sel) > 1:
            problems.append({"id": fid, "problem": f"'{exclusive[0]}' cannot be combined with other selections"})
    return problems


# ---------- flags ----------
def _flag(fid, severity, fields, gates, message):
    return {"flag_id": fid, "severity": severity, "fields": fields, "gates": gates, "message": message}


def evaluate(answers):
    """Apply D2.3 Section 5 rules. Severity: blocking | gap | info."""
    flags = []
    v = lambda fid: _val(answers, fid)
    act = lambda fid: is_active(fid, answers)
    sel = lambda fid: _selected(v(fid))

    # 1. Behaviour after release missing/unknown
    b = v("ACC-008")
    if not b or b == UNKNOWN:
        flags.append(_flag("FLG-01", "blocking", ["ACC-008"], "G8",
            "Behaviour after release is missing or Unknown. Do not assume the algorithm is locked."))

    # 2. 'Locked' contradicted by other answers
    if b == LOCKED:
        conflicts = []
        if v("ACC-007") in ("Configurable by site or user", "Adjusted automatically"):
            conflicts.append("ACC-007")
        if [x for x in sel("ACC-009") if x != "None"]:
            conflicts.append("ACC-009")
        if v("ACC-012") == "Yes":
            conflicts.append("ACC-012")
        if conflicts:
            flags.append(_flag("FLG-02", "blocking", ["ACC-008"] + conflicts, "G8",
                "Described as locked, but other answers indicate configurable, field-changing, or "
                "feedback-driven behaviour. Resolve the conflict before using the 'locked' answer."))

    # 3. Adaptive/site-configurable without safeguards or monitoring
    if b in (SITE, ADAPTIVE):
        no_safeguards = (not sel("ACC-011")) or set(sel("ACC-011")) <= {"None", UNKNOWN}
        no_monitor = (not sel("ACC-028")) or set(sel("ACC-028")) <= {"None", UNKNOWN}
        if no_safeguards or no_monitor:
            which = ([] if not no_safeguards else ["ACC-011"]) + ([] if not no_monitor else ["ACC-028"])
            flags.append(_flag("FLG-03", "blocking", ["ACC-008"] + which, "G4; G8; G10",
                "Adaptive or site-configurable behaviour without recorded safeguards, monitoring, or rollback."))

    # 4. Planned changes without a documented change plan
    if v("ACC-013") == "Yes" and act("ACC-019") and v("ACC-019") in ("No", UNKNOWN, None):
        flags.append(_flag("FLG-04", "gap", ["ACC-013", "ACC-019"], "G8; G9",
            "Changes are planned but no documented change plan exists or it is unknown. Do not treat the "
            "changes as pre-authorized, and do not assume no new submission or amendment is needed."))

    # 5. Planned change alters recorded profile
    if act("ACC-017") and v("ACC-017") in ("Yes", "Sometimes"):
        flags.append(_flag("FLG-05", "blocking", ["ACC-017"], "G1; G2; G8",
            "A planned change may alter intended use, population, inputs, outputs, or claims. Assess as a "
            "potential significant/substantial change in each framework separately, and re-complete "
            "D2.1 and D2.2 for the changed product."))

    # 6. Change plan status claimed without supporting document
    if act("ACC-020") and isinstance(v("ACC-020"), dict):
        claimed = [fw for fw, s in v("ACC-020").items() if s == "Authorized or accepted"]
        has_doc = bool((answers.get("ACC-019") or {}).get("details", "").strip()
                       or (answers.get("ACC-020") or {}).get("evidence", "").strip())
        if claimed and not has_doc:
            flags.append(_flag("FLG-06", "blocking", ["ACC-019", "ACC-020"], "G8; G9",
                f"Change plan reported as authorized/accepted ({', '.join(claimed)}) without a supporting "
                "document or correspondence. Treat as unverified."))

    # 7. Third-party components
    if v("ACC-005") == UNKNOWN:
        flags.append(_flag("FLG-07", "gap", ["ACC-005"], "G4; G5; G8",
            "Third-party or pre-trained component status is Unknown. Cross-reference D2.4 and D2.5."))

    # 8. Traceability of output to version/config
    if v("ACC-025") in ("No", "Partly", UNKNOWN):
        flags.append(_flag("FLG-08", "gap", ["ACC-025"], "G8; G10",
            "Algorithm version, training data, and configuration behind an output cannot be fully identified."))

    # 9. Required answers recorded as Unknown (excluding those already flagged blocking above)
    unknown_fields = []
    for f in FIELDS:
        fid = f["id"]
        if fid == "ACC-008" or not act(fid):
            continue
        if UNKNOWN in _selected(v(fid)):
            unknown_fields.append(fid)
    if unknown_fields:
        flags.append(_flag("FLG-09", "gap", unknown_fields, "G8",
            "Required answers recorded as Unknown. Information gaps must be resolved; they are never "
            "treated as a satisfied requirement."))

    # 10. Evidence references
    missing_ev = [f["id"] for f in FIELDS
                  if act(f["id"]) and not is_blank(f["type"], v(f["id"]))
                  and not (answers.get(f["id"]) or {}).get("evidence", "").strip()]
    if missing_ev:
        flags.append(_flag("FLG-10", "gap", missing_ev, "G8; G9",
            "Answers without an evidence reference (document ID, version, page/section). Research sources "
            "justify a field but do not prove a product claim; record as a documentation gap."))

    return flags


def profile_status(problems, flags):
    if any(f["severity"] == "blocking" for f in flags):
        return MANUAL_REVIEW
    if problems or any(f["severity"] == "gap" for f in flags):
        return STATUS_INCOMPLETE
    return STATUS_READY


def build_record(record_name, answers):
    """Assemble the exportable JSON record for one algorithm."""
    problems = validate(answers)
    flags = evaluate(answers)
    out_answers, not_applicable = {}, {}
    for f in FIELDS:
        fid = f["id"]
        if is_active(fid, answers):
            a = answers.get(fid) or {}
            out_answers[fid] = {"value": a.get("value"), "details": a.get("details", ""),
                                "evidence": a.get("evidence", "")}
        else:
            c = f["when"]
            not_applicable[fid] = f"Not applicable: {c['field']} does not trigger this field"
    return {
        "schema_version": "D2.3-draft-1",
        "record_name": record_name,
        "answers": out_answers,
        "not_applicable": not_applicable,
        "validation_problems": problems,
        "flags": flags,
        "profile_status": profile_status(problems, flags),
        "limitations": ("Planning aid only. Not legal or regulatory advice; not a classification, "
                        "compliance finding, or Go outcome. Framework-specific decision logic is D2.6."),
    }
