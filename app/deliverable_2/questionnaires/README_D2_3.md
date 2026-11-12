# D2.3 Algorithm and Change-Control Questionnaire

Self-contained module and Streamlit app for Deliverable 2.3 (ACC-001 to ACC-029).

| File | Purpose |
| --- | --- |
| `algorithm_change_control.py` | Schema (29 fields) and validation/flag logic. Edit the SCHEMA section to change questions. |
| `algorithm_change_control_app.py` | Streamlit interface; one record per algorithm; JSON load/export. |
| `test/test_algorithm_change_control.py` (repo root `test/`) | Scenario tests and an app smoke test. |

Run from this folder: `streamlit run algorithm_change_control_app.py`
Run tests from the repo root: `pytest test/test_algorithm_change_control.py`
(needs `pip install streamlit pytest`)

Planning aid only: collects facts, records gaps and conflicts, never produces a Go outcome or a
compliance finding. D1.6 requirement IDs and D2.6 rule IDs are pending verification; do not guess them.
Software is outside the Fall plan unless the team agrees a scope change, so treat as a prototype.
