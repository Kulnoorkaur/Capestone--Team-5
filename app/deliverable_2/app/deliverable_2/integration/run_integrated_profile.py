"""Team 5, D2.6: single-file integrated profile + four documented pathway trees.

Put this at app/deliverable_2/integration/run_integrated_profile.py.
Run from the GitHub repository root:
    python -m pip install "streamlit>=1.40" openpyxl
    python -m streamlit run app/deliverable_2/integration/run_integrated_profile.py

Conservative planning aid ONLY, not regulatory advice/classification/clearance.
"""
from __future__ import annotations
import csv
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import streamlit as st
from openpyxl import load_workbook

# Use the actual team-owned questionnaires; do not duplicate or overwrite them.
ROOT = Path(__file__).resolve().parents[3]
QUESTIONNAIRES = ROOT / "app" / "deliverable_2" / "questionnaires"
if str(QUESTIONNAIRES) not in sys.path:
    sys.path.insert(0, str(QUESTIONNAIRES))

from product_profile import render_product_profile, FIELD_LABELS as PIP_LABELS
from ai_function import render_ai_function, FIELD_LABELS as AIF_LABELS
from Dataset_and_evidence import render_dataset_evidence
from risk_documentation import render_risk_documentation, FIELD_LABELS as RISK_LABELS
from algorithm_change_control import (
    FIELDS as ACC_FIELDS, GROUPS as ACC_GROUPS, FRAMEWORKS as ACC_FRAMEWORKS,
    is_active as acc_is_active, needs_details as acc_needs_details,
    build_record as acc_build_record,
)

# Source of truth: the complete, populated D1.6 workbook (NOT the empty Book.xlsx).
MATRIX_PATH = ROOT / "reference" / "Team5_Regulatory_Requirements_Matrix_V1.xlsx"
FRAMEWORKS = ("Health Canada", "FDA", "EU MDR", "EU AI Act")
DISCLAIMER = (
    "Fall 2026 research/decision support only. No classification, regulatory clearance, "
    "authorization, compliance certification, gate pass, or clinical-use permission is assigned. "
    "All conclusions need qualified framework-specific regulatory review."
)

# Read the existing, numbered D1.6 requirements, source ID/pinpoint, status and UQs.
def read_matrix():
    if not MATRIX_PATH.is_file():
        return {}, ["D1.6 master matrix missing: place the populated XLSX in reference/."], []
    wb = load_workbook(MATRIX_PATH, read_only=True, data_only=True)
    try:
        if "Master Matrix" not in wb.sheetnames:
            return {}, ["Expected 'Master Matrix' worksheet is missing."], []
        raw = list(wb["Master Matrix"].values)
        if not raw or "Requirement ID" not in raw[0]:
            return {}, ["Master Matrix has no 'Requirement ID' header."], []
        rows = [{str(k).strip(): v for k, v in zip(raw[0], row) if k}
                for row in raw[1:] if row and any(x is not None for x in row)]
        records = {str(r["Requirement ID"]).strip(): r for r in rows
                   if r.get("Requirement ID")}
        issues = []
        if "Unresolved Questions" in wb.sheetnames:
            raw2 = list(wb["Unresolved Questions"].values)
            if raw2:
                issues = [{str(k).strip(): v for k, v in zip(raw2[0], row) if k}
                          for row in raw2[1:] if row and row[0]]
        return records, [], issues
    finally:
        wb.close()


def absent(value):
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return not text or text in {"select an option", "unknown", "not established", "tbd", "not sure"} \
            or text.startswith("unknown:") or text.startswith("unknown -") or text.startswith("unknown —")
    if isinstance(value, (list, tuple, set)):
        return not value or all(absent(v) for v in value)
    if isinstance(value, dict):
        return not value or all(absent(v) for v in value.values())
    return False


def collected_values(obj, fid):
    """Find a field inside all D2.1–D2.5 records, including nested D2.4 data.

    D2.3 stores {value,details,evidence} wrappers per algorithm; unwrap them.
    """
    matches = []
    def walk(x):
        if isinstance(x, dict):
            for key, value in x.items():
                if key == fid or (fid.startswith("DEP-") and key.startswith(fid + "-")):
                    if isinstance(value, dict) and "value" in value:
                        matches.append(value["value"])
                    else:
                        matches.append(value)
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(x, list):
            for value in x:
                walk(value)
    walk(obj)
    return matches


def one(profile, fid):
    values = collected_values(profile, fid)
    return values[0] if values else None


def required_for_record(profile, fid):
    # A D2.3 conditional question is required only if its trigger is met.
    if fid.startswith("ACC-"):
        models = profile.get("algorithms", [])
        return any(fid in m.get("answers", {}) for m in models)
    if fid == "DEP-025":
        return one(profile, "AIF-005") == "Yes"
    return True


def missing_fields(profile, fields):
    missing = []
    for fid in fields:
        if not required_for_record(profile, fid):
            continue
        vals = collected_values(profile, fid)
        # For multiple algorithm/dataset records, even one missing answer matters.
        if not vals or any(absent(v) for v in vals):
            missing.append(fid)
    return missing


# Documented trees: each node has source requirement IDs, profile inputs,
# evidence gates, and alternative regulatory-review branches.

"""Deliverable 2.6: Four distinct traceable DOCUMENTED decision-tree structures.

This is research decision support, not an automatically validated regulator classifier.
Each node retains a branching question, the source matrix IDs and field inputs.
"""

def node(rule_id, question, reqs, fields, gates, branches):
    return dict(rule_id=rule_id, question=question, requirement_ids=reqs,
                field_ids=fields, gate_ids=gates, branches=branches)

TREES={
 'Health Canada':[
  node('HC-D26-01','Does the stated medical purpose and image-processing function fall within the medical-device definition or SaMD guidance?',
       ['HC-CLS-01','HC-CLS-02'],['PIP-002','PIP-020','PIP-021','AIF-001'],['G1','G2'],
       ['Medical imaging function and medical-purpose claim stated → examine device definition and SaMD/CDS guidance',
        'Nonmedical or non-image function claimed → verify device status and exclusions against intended use',
        'Facts missing or contradictory → manual regulatory review required']),
  node('HC-D26-02','How do output role and seriousness of the clinical context affect the applicable Schedule 1 classification rules?',
       ['HC-CLS-03','HC-CLS-04'],['PIP-003','PIP-023','AIF-010','AIF-013'],['G2'],
       ['Output informs care → assess Health Canada SaMD role-and-situation table',
        'Output drives or performs diagnosis/treatment → assess corresponding higher-risk situations and Schedule 1 rules',
        'Role or harm severity unresolved → manual regulatory review required']),
  node('HC-D26-03','What evidence and licensing documentation would be needed for the candidate class and intended claims?',
       ['HC-LIC-01','HC-LIC-02','HC-LIC-03','HC-DAT-01','HC-PRF-01','HC-CLN-01'],
       ['DOC-004','DOC-001','DEP-001','DEP-019','DEP-027'],['G3','G5','G6','G9'],
       ['Regulated device with class determined by qualified review → use class-specific evidence/licensing requirements',
        'Missing product datasets, technical/clinical evidence, or classification → manual regulatory review required']),
  node('HC-D26-04','Is the algorithm locked, site-configurable, or adaptive, and could planned changes require a licence amendment or an authorized PCCP?',
       ['HC-CHG-01','HC-CHG-02'],['ACC-008','ACC-013','ACC-017','ACC-019'],['G8','G9'],
       ['Locked, no planned change → retain version/change-control documentation',
        'Updates or adaptive behaviour → assess significant change and PCCP applicability; approval cannot be presumed',
        'Change details/authorization unclear → manual regulatory review required']),
  node('HC-D26-05','Are risks, cybersecurity, user information, and ongoing monitoring identified for the proposed use?',
       ['HC-RSK-01','HC-CYB-01','HC-TRA-01','HC-TRA-02','HC-PMS-07'],
       ['RCD-001','RCD-002','CYB-001','UID-001','ACC-028'],['G4','G7','G10'],
       ['Documented facts available → map evidence to applicable requirements and verify manually',
        'Controls or post-market assumptions unresolved → manual regulatory review required']),
 ],
 'FDA':[
  node('FDA-D26-01','Does each intended software function meet the device definition, and does the non-device CDS exclusion apply?',
       ['FDA-APP-01','FDA-APP-02'],['PIP-002','PIP-020','AIF-001','AIF-010','AIF-017'],['G1','G2'],
       ['Function analyzes medical images → independently assess the FDA software-function exclusion criteria',
        'Clinician can independently review basis → assess all statutory CDS conditions, not this fact alone',
        'Missing function/clinical role → manual regulatory review required']),
  node('FDA-D26-02','Which FDA regulation, product code, risk class, predicate status and potential premarket pathway fit the actual intended use?',
       ['FDA-CLS-01','FDA-CLS-02','FDA-PRE-01'],
       ['PIP-002','PIP-012','AIF-006','AIF-013','INT-004'],['G2','G9'],
       ['Suitable classification and predicate documented → have reviewer assess 510(k) possibility',
        'No suitable predicate → discuss De Novo/PMA and FDA engagement as appropriate, no automatic selection',
        'Search, class, or clinical claim unverified → manual regulatory review required']),
  node('FDA-D26-03','What datasets, device-performance and clinical evidence substantiate the intended claims?',
       ['FDA-DAT-01','FDA-PRF-01','FDA-CLN-01'],['DEP-001','DEP-019','DEP-020','DEP-027','DEP-035'],['G3','G5','G6','G9'],
       ['Version-matched technical/clinical evidence documented → check adequacy under selected regulatory pathway',
        'Evidence, version linkage or applicability unknown → manual regulatory review required']),
  node('FDA-D26-04','Does the software-change strategy require a new marketing submission or support a reviewed PCCP?',
       ['FDA-CHG-01','FDA-CHG-02'],['ACC-008','ACC-013','ACC-017','ACC-019','ACC-020'],['G8','G9','G10'],
       ['No planned modification → preserve version and change procedure',
        'Planned modification → examine applicable software-change guidance and PCCP document/status',
        'PCCP not documented or authorization unverified → manual regulatory review required']),
  node('FDA-D26-05','Are risk, cyber-device applicability, transparent user information and post-market processes adequately characterized?',
       ['FDA-RSK-01','FDA-CYB-01','FDA-TRA-01','FDA-PMS-03'],
       ['RCD-001','CYB-001','CYB-003','UID-001','ACC-028'],['G4','G7','G10'],
       ['Facts recorded → review cyber-device status and requirements conditionally',
        'Risk/cybersecurity/monitoring facts absent → manual regulatory review required']),
 ],
 'EU MDR':[
  node('MDR-D26-01','Does the intended medical purpose qualify the software as a medical device, and is MDR rather than IVDR the applicable framework?',
       ['MDR-QUA-01','MDR-QUA-02'],['PIP-002','PIP-005','PIP-006','PIP-021','AIF-001'],['G1','G2'],
       ['Imaging-derived medical purpose → assess MDR software qualification and any IVDR boundary',
        'Specimen/in-vitro-derived information → evaluate the IVDR boundary independently',
        'Source and intended purpose unknown → manual regulatory review required']),
  node('MDR-D26-02','How do the clinical decision and consequences of error affect Annex VIII Rule 11 or other rules?',
       ['MDR-CLS-01','MDR-CLS-02','MDR-CLS-03'],['PIP-023','AIF-010','AIF-013','AIF-016'],['G2'],
       ['Diagnostic/therapeutic decisions supported → assess Rule 11 class and harm-severity branches',
        'Software drives another device → assess applicable inherited classification and highest rule',
        'Seriousness/decision role undetermined → manual regulatory review required']),
  node('MDR-D26-03','What Notified Body and conformity-assessment route applies to the reviewer-confirmed class?',
       ['MDR-CON-01','MDR-CON-02','MDR-CON-03'],['DOC-004','DOC-001','INT-004'],['G2','G9'],
       ['Reviewer-confirmed class IIa/IIb/III → examine NB conformity route',
        'Reviewer-confirmed eligible Class I → examine the appropriate self-declaration route',
        'Class, NB status or documentation uncertain → manual regulatory review required']),
  node('MDR-D26-04','Are performance, clinical evaluation, risk, cybersecurity and labeling evidence recorded for the device?',
       ['MDR-EVD-01','MDR-DAT-01','MDR-PRF-01','MDR-CLN-01','MDR-RSK-01','MDR-CYB-01','MDR-TRA-01'],
       ['DEP-001','DEP-019','DEP-027','RCD-001','CYB-001','UID-001'],['G3','G4','G5','G6','G7','G9'],
       ['Product evidence known → perform GSPR/evaluation traceability review',
        'Evidence missing or unverified → manual regulatory review required']),
  node('MDR-D26-05','Do planned changes affect the certified device, change control, or post-market surveillance?',
       ['MDR-CHG-01','MDR-PMS-01'],['ACC-008','ACC-013','ACC-017','ACC-022','ACC-028'],['G8','G10'],
       ['Changes planned → examine NB change procedures and intended-use impact',
        'No changes planned → retain version history and PMS documentation',
        'Change scope unclear → manual regulatory review required']),
 ],
 'EU AI Act':[
  node('AIA-D26-01','Is the system an AI system under Article 3 and within the geographic, actor and lifecycle scope of the AI Act?',
       ['AIA-APP-01','AIA-APP-02','AIA-APP-03'],
       ['PIP-002','AIF-004','ACC-003','INT-001','INT-002','INT-003'],['G1','G2'],
       ['EU market/use and covered actor claimed → examine Article 2 scope',
        'Research-only claimed → inspect conditions and exclusions; do not presume research exemption',
        'AI-system definition or territorial role unclear → manual regulatory review required']),
  node('AIA-D26-02','Does Article 6(1) high-risk qualification apply to a covered Annex I medical-device product or safety component requiring third-party assessment?',
       ['AIA-CLS-01','AIA-CON-01'],['PIP-002','AIF-010','INT-004','INT-005'],['G2','G9'],
       ['Annex I product/safety component AND third-party conformity requirement documented → assess Art. 6(1) high-risk route',
        'One condition not met → independently consider any other AI Act high-risk bases',
        'MDR/IVDR class, NB procedure or AI role unknown → manual regulatory review required']),
  node('AIA-D26-03','For a high-risk product, are technical documentation, training data governance and performance requirements addressed?',
       ['AIA-DAT-01','AIA-DOC-01','AIA-PRF-01','AIA-QMS-01'],
       ['DEP-001','DEP-007','DEP-014','DEP-019','DOC-001','RCD-001'],['G3','G4','G5','G6','G9'],
       ['High-risk status established by reviewer → assess the associated Articles 9–17 requirements',
        'High-risk status or evidence missing → manual regulatory review required']),
  node('AIA-D26-04','If high-risk, are logging, transparency and effective human oversight provided?',
       ['AIA-LOG-01','AIA-TRA-01','AIA-HOV-01'],['ACC-025','AIF-017','AIF-018','AIF-019','UID-001'],['G4','G7','G10'],
       ['Oversight and traceability documented → validate applicability/adequacy with reviewed sources',
        'Autonomy, oversight or records unresolved → manual regulatory review required']),
  node('AIA-D26-05','Do deployment, monitoring and algorithm modification trigger additional high-risk obligations or substantial-modification review?',
       ['AIA-CHG-01','AIA-PMS-01','AIA-PMS-02'],['ACC-008','ACC-013','ACC-017','ACC-025','ACC-028'],['G8','G10'],
       ['Changes planned → assess substantial modification and renewed assessment implications',
        'No changes planned → maintain lifecycle records and monitoring',
        'Change behaviour or monitoring unspecified → manual regulatory review required']),
 ],
}


# Labels are taken from the existing team dictionary / scripts.
DEP_TITLES = """Dataset Inventory|Sources, Sites and Collection Period|Collection Design|Ethics, Consent, Data-Use and Privacy|Sample Sizes|Inclusion and Exclusion Criteria|Population Composition|Acquisition Characteristics|Preprocessing and Quality Control|Data Management and Traceability|Reference Standard|Expert Selection and Agreement|Reference Standard Limitations|Partitioning and Independence|External or Independent Test Data|Dataset Representativeness|Bias Assessment and Mitigation|Known Data Gaps|Evaluated Software and Model Versions|Metrics and Acceptance Criteria|Overall and Subgroup Results|Repeatability and Reproducibility|Robustness and Failure Testing|Output Uncertainty|Generated or Modified Outputs|Software Verification and Validation|Valid Clinical Association|Clinical Performance Evidence Type|Clinical Study Population and Independence|Clinical Performance Measures and Results|Human-AI Team Evaluation|Evidence-to-Claim Alignment|Rationale Without Device-Specific Clinical Data|Planned Human Studies|Evidence Document Register|GMLP Implementation""".split("|")
INT_LABELS = {
    "INT-001": "Target jurisdictions/markets",
    "INT-002": "Legal roles, locations, EU placement/use",
    "INT-003": "Development and deployment stage",
    "INT-004": "FDA classification/predicate and EU MDR class/NB documentation",
    "INT-005": "EU AI Act Article 6(1) two-part test and evidence",
}
FIELD_LABELS = {**PIP_LABELS, **AIF_LABELS, **RISK_LABELS,
                **{f"DEP-{n:03d}": name for n, name in enumerate(DEP_TITLES, 1)},
                **{f["id"]: f["label"] for f in ACC_FIELDS}, **INT_LABELS}


def data_dictionary():
    out = []
    group_by_prefix = {"PIP": "D2.1", "AIF": "D2.2", "ACC": "D2.3",
                       "DEP": "D2.4", "RCD": "D2.5", "CYB": "D2.5",
                       "UID": "D2.5", "DOC": "D2.5", "INT": "D2.6 (proposed)"}
    rules_for = defaultdict(set)
    for fw, rules in TREES.items():
        for rule in rules:
            for fid in rule["field_ids"]:
                rules_for[fid].add(rule["rule_id"])
    for fid, name in sorted(FIELD_LABELS.items()):
        out.append({"field_id": fid, "label": name,
                    "owner_section": group_by_prefix.get(fid.split("-")[0], "Review"),
                    "direct_tree_rules": "; ".join(sorted(rules_for[fid])),
                    "change_status": "Proposed; team approval required" if fid.startswith("INT-")
                                     else "Original team field ID"})
    return out


def crosswalk(requirements):
    """All 84 matrix rows retained; non-tree records remain evidence/gate checks."""
    by_req = defaultdict(list)
    by_fields = defaultdict(set)
    for fw, rules in TREES.items():
        for rule in rules:
            for req in rule["requirement_ids"]:
                by_req[req].append(rule["rule_id"])
                by_fields[req].update(rule["field_ids"])
    out = []
    for rid, r in requirements.items():
        out.append({
            "requirement_id": rid,
            "framework": r.get("Framework") or "",
            "requirement_type": r.get("Requirement Type") or "",
            "source_ids": r.get("Primary Source ID(s)") or "",
            "source_pinpoint": r.get("Exact Section / Article / Clause") or "",
            "related_gates": r.get("Related Gate(s)") or "",
            "profile_field_ids": "; ".join(sorted(by_fields[rid])),
            "decision_rule_ids": "; ".join(by_req[rid]),
            "mapping_status": "Direct D2.6 tree node" if by_req[rid]
                              else "Evidence-only / gate mapping; manual linkage review",
            "review_status": r.get("Review Status") or "",
            "unresolved_question_id": r.get("Unresolved Question ID") or "",
        })
    return out


def to_csv(rows):
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys(), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def d23_flags(profile):
    issues = []
    for ix, record in enumerate(profile.get("algorithms", []), 1):
        for problem in record.get("validation_problems", []):
            issues.append({"issue_id": f"D26-ACC-{ix}-{problem['id']}-ANSWER",
                           "framework": "All four", "fields": problem["id"],
                           "reason": problem["problem"],
                           "action": "Correct the D2.3 answer or explain/evidence the gap."})
        for flag in record.get("flags", []):
            if flag["severity"] in ("gap", "blocking"):
                issues.append({"issue_id": f"D26-ACC-{ix}-{flag['flag_id']}",
                               "framework": "All four", "fields": ", ".join(flag["fields"]),
                               "reason": flag["message"],
                               "action": "Resolve with D2.3 owner and regulatory reviewer."})
    return issues


def additional_issues(profile):
    issues = []
    def add(tag, fields, why, action):
        issues.append({"issue_id": "D26-" + tag, "framework": "All four",
                       "fields": ", ".join(fields), "reason": why, "action": action})
    # D2.3 itself performs detailed ACC-008/009 and ACC-020 checks.
    if one(profile, "AIF-005") == "Yes" and absent(one(profile, "DEP-025")):
        add("GENERATED-IMAGE-EVIDENCE", ["AIF-005", "DEP-025"],
            "Image generation/modification is claimed but supporting evidence is absent.",
            "Record generated-image performance evidence and limitations in D2.4.")
    datasets = (profile.get("dataset_evidence") or {}).get("datasets", [])
    if not datasets:
        add("DATASET-EMPTY", ["DEP-001"], "No dataset record found.",
            "Complete at least one dataset inventory; identify dataset role and version.")
    if one(profile, "ACC-017") in ("Yes", "Sometimes"):
        add("CHANGE-INTENDED-USE", ["ACC-017", "PIP-002", "AIF-010"],
            "A planned model change may change intended use, population, outputs or claims.",
            "Update D2.1/D2.2 and reassess each framework separately.")
    return issues


def suggested_branch(profile, framework, rule):
    """Return only a review branch, never an automatic class or pathway."""
    rid = rule["rule_id"]
    branches = rule["branches"]
    # The alternatives are documented, but one path cannot be legally confirmed
    # without device-specific assessment. We flag the preliminary fact pattern.
    if rid in {"HC-D26-04", "FDA-D26-04", "MDR-D26-05", "AIA-D26-05"}:
        if one(profile, "ACC-013") == "Yes":
            return "Planned change identified — review change significance/PCCP in this framework: " + branches[0]
        return "No planned change reported — verify version/lifecycle: " + branches[0]
    if rid in {"HC-D26-01", "FDA-D26-01"}:
        image_inputs = one(profile, "AIF-001")
        if isinstance(image_inputs, list) and "Medical images" in image_inputs:
            return "Medical-image processing reported — evaluate device status and CDS exclusions; " + branches[0]
    if rid == "AIA-D26-02":
        return "Article 6(1) Annex I + third-party conformity test requires expert confirmation; " + branches[0]
    return "Potential review branch (not a finding): " + branches[0]


def assess(profile, requirements, matrix_warnings, matrix_questions):
    global_issues = d23_flags(profile) + additional_issues(profile)
    results = {}
    issue_rows = list(global_issues)
    for fw, rules in TREES.items():
        output = []
        for rule in rules:
            missing = missing_fields(profile, rule["field_ids"])
            mapped = [requirements.get(rid) for rid in rule["requirement_ids"]]
            missing_reqs = [rid for rid, record in zip(rule["requirement_ids"], mapped)
                            if not record]
            missing_sources = [rid for rid, record in zip(rule["requirement_ids"], mapped)
                               if record and (not record.get("Primary Source ID(s)")
                                              or not record.get("Exact Section / Article / Clause"))]
            linked_issues = [x for x in global_issues
                             if set(re.findall(r"[A-Z]{3}-\d{3}", x["fields"])) & set(rule["field_ids"])]
            problems = bool(missing or missing_reqs or missing_sources or linked_issues or matrix_warnings)
            if problems:
                outcome = "MANUAL REGULATORY REVIEW REQUIRED"
                branch = rule["branches"][-1]  # tree's unresolved branch
            else:
                outcome = "PROVISIONAL FACT PATTERN — QUALIFIED REVIEW REQUIRED"
                branch = suggested_branch(profile, fw, rule)
            for fid in missing:
                issue_rows.append({"issue_id": f"{rule['rule_id']}-{fid}-GAP",
                                   "framework": fw, "fields": fid,
                                   "reason": "Missing or Unknown fact for this decision node.",
                                   "action": "Enter accurate fact, explanation and product evidence."})
            for rid in missing_reqs + missing_sources:
                issue_rows.append({"issue_id": f"{rule['rule_id']}-{rid}-SOURCE",
                                   "framework": fw, "fields": "",
                                   "reason": "D1.6 requirement missing or lacks source/pinpoint.",
                                   "action": "Check and peer-review the 1.6 matrix record."})
            output.append({"rule_id": rule["rule_id"], "question": rule["question"],
                           "status": outcome, "selected_branch": branch,
                           "all_documented_branches": rule["branches"],
                           "field_ids": rule["field_ids"], "requirement_ids": rule["requirement_ids"],
                           "gate_ids": rule["gate_ids"], "missing_fields": missing,
                           "sources": [{"id": rid,
                                        "source": (r or {}).get("Primary Source ID(s)"),
                                        "pinpoint": (r or {}).get("Exact Section / Article / Clause"),
                                        "review_status": (r or {}).get("Review Status"),
                                        "unresolved_question": (r or {}).get("Unresolved Question ID")}
                                       for rid, r in zip(rule["requirement_ids"], mapped)],
                           "assumptions": ["Entered facts accurately represent developer's intended use.",
                                           "Matrix citations, dates, applicability and source hierarchy require review."],
                           "next_action": "Resolve the gaps and document an expert-reviewed jurisdiction-specific rationale."})
        results[fw] = {"outcome": "MANUAL REGULATORY REVIEW REQUIRED" if any(
            n["status"] == "MANUAL REGULATORY REVIEW REQUIRED" for n in output)
                       else "PROVISIONAL REVIEW ONLY", "nodes": output}
    return {"version": "D2.6-V1", "disclaimer": DISCLAIMER,
            "frameworks": results, "issue_log": issue_rows,
            "matrix_warnings": matrix_warnings,
            "matrix_questions_from_d1_6": matrix_questions,
            "matrix_requirement_count": len(requirements),
            "dictionary_count": len(FIELD_LABELS)}


def render_algorithm_answers():
    st.header("D2.3 — Algorithm and change-control fields")
    st.caption("Uses the exact supplied algorithm_change_control.py schema and validations. "
               "One record per model; conditional questions appear only when triggered.")
    count = int(st.number_input("Number of algorithms/models", min_value=1,
                                max_value=20, value=1, step=1, key="d26-model-count"))
    models = []
    for index in range(count):
        with st.expander(f"Algorithm {index + 1}", expanded=(index == 0)):
            name = st.text_input("Algorithm record name", value=f"Algorithm {index + 1}",
                                 key=f"d26-model-{index}-name")
            answers, previous_group = {}, None
            for field in ACC_FIELDS:
                fid = field["id"]
                if not acc_is_active(fid, answers):
                    continue
                if field["group"] != previous_group:
                    st.subheader(field["group"])
                    previous_group = field["group"]
                st.markdown(f"**{fid} — {field['label']}**")
                if field.get("help"):
                    st.caption(field["help"])
                key = f"d26-model-{index}-{fid}"
                typ = field["type"]
                if typ == "text":
                    value = st.text_input("Answer", key=key, label_visibility="collapsed")
                elif typ == "longtext":
                    value = st.text_area("Answer", key=key, label_visibility="collapsed")
                elif typ == "select":
                    value = st.selectbox("Answer", field["options"], index=None,
                                         key=key, label_visibility="collapsed",
                                         placeholder="Select one")
                elif typ == "multiselect":
                    value = st.multiselect("Answer", field["options"], key=key,
                                           label_visibility="collapsed")
                else:  # D2.3 per-framework regulatory-change-plan status
                    cols = st.columns(len(ACC_FRAMEWORKS))
                    value = {}
                    for col, fw in zip(cols, ACC_FRAMEWORKS):
                        with col:
                            value[fw] = st.selectbox(fw, field["options"], index=None,
                                                     key=f"{key}-{fw}", placeholder="Select")
                details = st.text_area("Explanation / details", key=f"{key}-details") \
                    if acc_needs_details(fid, value) else ""
                evidence = st.text_input("Evidence: document ID, version, page/section",
                                         key=f"{key}-evidence")
                answers[fid] = {"value": value, "details": details, "evidence": evidence}
            models.append(acc_build_record(name, answers))
    return models


st.set_page_config(page_title="Team 5 | Integrated Imaging-AI Profile", layout="wide")
st.caption("ENGG 501 · TEAM 5 · DELIVERABLE 2.6 · INTEGRATION LEAD: CHANDRIMA")
st.title("Imaging-AI Product Profile V1 — Integrated")
st.info(DISCLAIMER)
requirements, matrix_warnings, matrix_questions = read_matrix()
if matrix_warnings:
    for warning in matrix_warnings:
        st.error(warning)
else:
    st.caption(f"D1.6 matrix loaded: {len(requirements)} unique requirement records. "
               "Research status remains draft until reviewer sign-off.")

pages = st.tabs(["D2.1 Product", "D2.2 AI function", "D2.3 Algorithm/change",
                 "D2.4 Datasets/evidence", "D2.5 Risk/cyber/docs", "D2.6 Scope inputs",
                 "D2.6 Decision trees and exports"])
with pages[0]:
    product = render_product_profile()
with pages[1]:
    ai_function = render_ai_function()
with pages[2]:
    algorithms = render_algorithm_answers()
with pages[3]:
    datasets = render_dataset_evidence()
with pages[4]:
    risk = render_risk_documentation()
with pages[5]:
    st.header("D2.6 — Proposed integration-only questions")
    st.caption("These five fields fill the market/pathway-scope gaps. They are not substitutes "
               "for the five owner questionnaires; team approval is required.")
    integration = {
        "INT-001": st.multiselect("INT-001 — Which target markets?",
                                  ["Canada", "United States", "European Union", "Unknown"],
                                  key="d26-INT-001"),
        "INT-002": st.text_area("INT-002 — Manufacturer/provider/deployer roles, locations, EU use",
                                key="d26-INT-002", placeholder="Facts and evidence, or Unknown: reason"),
        "INT-003": st.selectbox("INT-003 — Product development/deployment stage",
                                ["Select an option", "Research only", "Validation/testing", "Premarket",
                                 "Marketed/clinical deployment", "Unknown"], key="d26-INT-003"),
        "INT-004": st.text_area("INT-004 — FDA class/product-code/predicate and EU MDR class/NB evidence",
                                key="d26-INT-004", placeholder="Reviewer assessment/document ID, or Unknown: reason"),
        "INT-005": st.text_area("INT-005 — AI Act Art. 6(1) Annex I AND third-party-assessment analysis",
                                key="d26-INT-005", placeholder="Two-part test, reviewer, and evidence; or Unknown: reason"),
    }
with pages[6]:
    st.header("D2.6 — Four framework-specific decision trees")
    st.write("Run only after answering the relevant fields. Unknown/contradictory inputs "
             "are routed to manual regulatory review; no automatic legal classification is issued.")
    if st.button("Evaluate integrated profile", type="primary"):
        profile = {"schema_version": "D2.6-V1", "product": product,
                   "ai_function": ai_function, "algorithms": algorithms,
                   "dataset_evidence": datasets, "risk_documentation": risk,
                   "integration": integration}
        st.session_state["d26-profile"] = profile
        st.session_state["d26-results"] = assess(profile, requirements, matrix_warnings,
                                                  matrix_questions)
    result = st.session_state.get("d26-results")
    if result:
        a, b, c = st.columns(3)
        a.metric("Profile data dictionary fields", result["dictionary_count"])
        b.metric("D1.6 requirement records", result["matrix_requirement_count"])
        c.metric("D2.6 tree nodes", sum(len(x["nodes"]) for x in result["frameworks"].values()))
        for fw, tree in result["frameworks"].items():
            st.subheader(f"{fw}: {tree['outcome']}")
            for node in tree["nodes"]:
                with st.expander(f"{node['rule_id']} · {node['question']}"):
                    st.write("**Status:**", node["status"])
                    st.write("**Selected review branch:**", node["selected_branch"])
                    st.write("**All branches:**", node["all_documented_branches"])
                    st.write("**Input IDs:**", ", ".join(node["field_ids"]))
                    st.write("**D1.6 requirement IDs:**", ", ".join(node["requirement_ids"]))
                    st.write("**Gates:**", ", ".join(node["gate_ids"]))
                    if node["missing_fields"]:
                        st.warning("Missing or Unknown: " + ", ".join(node["missing_fields"]))
                    st.write("**Source traceability (research draft):**")
                    st.dataframe(node["sources"], hide_index=True, use_container_width=True)
                    st.write("**Assumptions:**", node["assumptions"])
                    st.write("**Next action:**", node["next_action"])
        st.subheader("D2.6 issue log")
        st.dataframe(result["issue_log"], hide_index=True, use_container_width=True)
        if result["matrix_questions_from_d1_6"]:
            with st.expander("Outstanding 1.6 matrix questions (separate research issue log)"):
                st.dataframe(result["matrix_questions_from_d1_6"], use_container_width=True)
        st.download_button("Download integrated profile (JSON)",
                           json.dumps(st.session_state["d26-profile"], indent=2, default=str),
                           "D2_6_integrated_profile.json", "application/json")
        st.download_button("Download four decision trees + issues (JSON)",
                           json.dumps(result, indent=2, default=str),
                           "D2_6_decision_trees.json", "application/json")
        st.download_button("Download field dictionary (CSV)", to_csv(data_dictionary()),
                           "D2_6_field_dictionary.csv", "text/csv")
        st.download_button("Download D1.6 traceability crosswalk (CSV)",
                           to_csv(crosswalk(requirements)),
                           "D2_6_traceability_crosswalk.csv", "text/csv")
    else:
        st.caption("No data evaluated yet. Fill in the profile and click Evaluate.")
