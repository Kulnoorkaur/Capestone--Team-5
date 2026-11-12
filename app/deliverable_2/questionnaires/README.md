# D2.3 Algorithm and Change-Control Questionnaire

Streamlit questionnaire for **Deliverable 2.3** (ACC-001 to ACC-029) of the Team 5
Imaging-AI Product Profile V1. It implements the questionnaire, conditional logic,
and the Section 5 handling rules (missing, conflicting, and uncertain information).

**Scope note:** this is a planning aid that supports the documents. It collects facts, records
gaps and conflicts, and exports JSON. It does not classify a product, certify compliance, or produce
a Go outcome. Software was outside the Fall plan unless added by an agreed scope change, so treat
it as a prototype until the team confirms.

## Run

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
pytest
```

## Layout

| Path | Purpose |
| --- | --- |
| `questionnaire/schema.py` | All 29 fields: question, type, options, required/conditional, gate links. **Edit here** to change the questionnaire. |
| `questionnaire/logic.py` | Conditional visibility, validation, and flag rules (FLG-01 to FLG-10). |
| `app.py` | Streamlit interface; one record per algorithm; JSON load/export. |
| `tests/` | Scenario tests (locked, adaptive, conflicting, incomplete) and an app smoke test. |

## Behaviour that matches D2.3

- Conditional fields hidden when their trigger is not met and exported as "not applicable".
- Unknown, "Other", and detail-triggering answers require an explanation.
- Locked-versus-configurable conflicts, adaptive behaviour without safeguards or monitoring,
  and planned changes that alter the recorded profile return **"manual regulatory review required"**.
- Planned changes without a documented change plan, and answers without evidence references, are
  recorded as gaps; the profile can never reach the "ready" status while gaps remain.
- Change-plan status (ACC-020) is recorded per framework; one framework never carries over to another.

## Still pending (do not guess)

- D1.6 requirement IDs and D2.6 decision-rule IDs: add to `schema.py` only after verification.
- Field IDs, Unknown/Other conventions, and repeatable-record handling to be agreed with D2.1, D2.2, D2.4, D2.5.
- Keep `schema.py` in sync with the D2.3 document whenever either changes.
