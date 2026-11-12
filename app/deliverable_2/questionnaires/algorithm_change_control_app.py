"""Streamlit questionnaire for Deliverable 2.3 (algorithm and change-control fields).

Run (from this folder):  streamlit run algorithm_change_control_app.py
"""
import json
import streamlit as st

from algorithm_change_control import (FIELDS, GROUPS, FRAMEWORKS, UNKNOWN, is_active, needs_details,
                                      build_record, validate, evaluate, profile_status, MANUAL_REVIEW)

st.set_page_config(page_title="D2.3 Algorithm & Change-Control Profile", layout="wide")
st.title("Imaging-AI Product Profile: Algorithm and Change-Control Fields (D2.3)")
st.caption("Planning aid for Team 5. Collects facts only; it does not classify the product, "
           "certify compliance, or produce a Go outcome. Unknown answers are never treated as favourable.")

# ---------- record management (one record per algorithm/model) ----------
if "records" not in st.session_state:
    st.session_state.records = {0: "Algorithm 1"}
    st.session_state.next_id = 1


def key(rid, fid, part):
    return f"{rid}|{fid}|{part}"


with st.sidebar:
    st.header("Algorithm records")
    st.write("Use a separate record for each model with a different purpose or change behaviour.")
    rid = st.radio("Active record", list(st.session_state.records),
                   format_func=lambda r: st.session_state.records[r])
    new_name = st.text_input("Rename active record", st.session_state.records[rid], key=f"name{rid}")
    st.session_state.records[rid] = new_name or st.session_state.records[rid]
    if st.button("Add record"):
        n = st.session_state.next_id
        st.session_state.records[n] = f"Algorithm {n + 1}"
        st.session_state.next_id += 1
        st.rerun()

    st.divider()
    up = st.file_uploader("Load saved record (JSON)", type="json")
    if up is not None and st.button("Load into active record"):
        data = json.load(up)
        for fid, a in data.get("answers", {}).items():
            st.session_state[key(rid, fid, "v")] = a.get("value")
            st.session_state[key(rid, fid, "d")] = a.get("details", "")
            st.session_state[key(rid, fid, "e")] = a.get("evidence", "")
            if isinstance(a.get("value"), dict):
                for fw, s in a["value"].items():
                    st.session_state[key(rid, fid, f"v_{fw}")] = s
        st.rerun()


# ---------- widgets ----------
def render(f, rid):
    fid = f["id"]
    label = f"**{fid}**  {f['label']}"
    st.markdown(label)
    if f["help"]:
        st.caption(f["help"])
    kv = key(rid, fid, "v")
    if f["type"] == "text":
        value = st.text_input(fid, key=kv, label_visibility="collapsed")
    elif f["type"] == "longtext":
        value = st.text_area(fid, key=kv, label_visibility="collapsed")
    elif f["type"] == "select":
        value = st.selectbox(fid, f["options"], index=None, key=kv, label_visibility="collapsed",
                             placeholder="Select one")
    elif f["type"] == "multiselect":
        value = st.multiselect(fid, f["options"], key=kv, label_visibility="collapsed")
    else:  # perframework
        cols = st.columns(len(FRAMEWORKS))
        value = {}
        for col, fw in zip(cols, FRAMEWORKS):
            with col:
                value[fw] = st.selectbox(fw, f["options"], index=None,
                                         key=key(rid, fid, f"v_{fw}"), placeholder="Select")
    details = ""
    if needs_details(fid, value):
        details = st.text_area("Explanation / details (required for this answer)",
                               key=key(rid, fid, "d"))
    evidence = st.text_input("Evidence reference (document ID, version, page/section)",
                             key=key(rid, fid, "e"))
    st.divider()
    return {"value": value, "details": details, "evidence": evidence}


# ---------- main form ----------
answers = {}
tabs = st.tabs(GROUPS + ["Review and export"])
for tab, group in zip(tabs, GROUPS):
    with tab:
        st.subheader(group)
        for f in [x for x in FIELDS if x["group"] == group]:
            if is_active(f["id"], answers):
                answers[f["id"]] = render(f, rid)
            else:
                st.caption(f"{f['id']}: not applicable (trigger not met), recorded as such.")

with tabs[-1]:
    name = st.session_state.records[rid]
    problems = validate(answers)
    flags = evaluate(answers)
    status = profile_status(problems, flags)

    if status == MANUAL_REVIEW:
        st.error(f"Outcome for **{name}**: {MANUAL_REVIEW}")
    elif problems or any(f["severity"] == "gap" for f in flags):
        st.warning(f"Status for **{name}**: {status}")
    else:
        st.success(f"Status for **{name}**: {status}")

    st.subheader("Missing or malformed answers")
    if problems:
        for p in problems:
            st.write(f"- **{p['id']}**: {p['problem']}")
    else:
        st.write("None.")

    st.subheader("Flags")
    if flags:
        for fl in flags:
            icon = {"blocking": "\U0001F534", "gap": "\U0001F7E0", "info": "\U0001F535"}[fl["severity"]]
            st.write(f"{icon} **{fl['flag_id']}** ({fl['severity']}; gates {fl['gates']}; "
                     f"fields {', '.join(fl['fields'])}): {fl['message']}")
    else:
        st.write("No flags.")

    record = build_record(name, answers)
    st.download_button("Download record (JSON)", json.dumps(record, indent=2),
                       file_name=f"{name.replace(' ', '_')}_D2_3.json", mime="application/json")
    st.caption("Store exported records in the repo's data/ folder only if they contain no confidential "
               "product information.")
