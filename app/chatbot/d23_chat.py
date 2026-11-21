"""Deterministic, algorithm-scoped conversation for D2.3."""

import streamlit as st

from app.chatbot.d23_adapter import D23AnswerAdapter
from app.deliverable_2.questionnaires.algorithm_change_control import (
    BY_ID,
    FRAMEWORKS,
    is_blank,
    needs_details,
)


def _identity(record):
    return f"{record['name']} — {record['version'] or 'version not provided'}"


def _complete(field_id, answer):
    value = answer.get("value")
    return not is_blank(BY_ID[field_id]["type"], value) and (
        not needs_details(field_id, value) or bool(answer["details"].strip())
    )


def _answer_input(definition, current, key):
    field_type = definition["type"]
    options = definition["options"]
    if field_type == "text":
        return st.text_input("Answer", value=current or "", key=key)
    if field_type == "longtext":
        return st.text_area("Answer", value=current or "", key=key)
    if field_type == "select":
        index = options.index(current) if current in options else None
        return st.selectbox("Answer", options, index=index, key=key)
    if field_type == "multiselect":
        return st.multiselect("Answer", options, default=current or [], key=key)

    statuses = current or {}
    return {
        framework: st.selectbox(
            framework,
            options,
            index=options.index(statuses[framework]) if statuses.get(framework) in options else None,
            key=f"{key}-{framework}",
        )
        for framework in FRAMEWORKS
    }


def render_d23_chat():
    state = st.session_state
    if "d23_adapter" not in state:
        state.d23_adapter = D23AnswerAdapter()
        state.d23_answer_revision = 0
    adapter = state.d23_adapter

    st.subheader("D2.3 — Algorithm Change Control")
    with st.chat_message("assistant"):
        st.write("Which algorithm are you describing? Select one or enter its name and version.")

    with st.expander("Add an algorithm", expanded=not adapter.algorithm_ids):
        with st.form("d23-add-algorithm", clear_on_submit=True):
            name = st.text_input("Algorithm name", key="d23-new-name")
            version = st.text_input("Algorithm version", key="d23-new-version")
            add = st.form_submit_button("Add algorithm")
        if add:
            try:
                algorithm_id = adapter.add_algorithm(name, version)
            except ValueError as error:
                st.error(str(error))
            else:
                state["d23-algorithm-picker"] = algorithm_id

    if not adapter.algorithm_ids:
        return

    if "d23-algorithm-picker" not in state:
        state["d23-algorithm-picker"] = state.get("d23_active_algorithm_id", adapter.algorithm_ids[0])
    algorithm_id = st.selectbox(
        "Selected algorithm",
        adapter.algorithm_ids,
        format_func=lambda item: f"{_identity(adapter.get_algorithm(item))} ({item})",
        key="d23-algorithm-picker",
    )
    state.d23_active_algorithm_id = algorithm_id
    algorithm = adapter.get_algorithm(algorithm_id)

    with st.expander("Edit algorithm name or version"):
        with st.form(f"d23-identity-{algorithm_id}"):
            name = st.text_input("Name", value=algorithm["name"], key=f"d23-name-{algorithm_id}")
            version = st.text_input("Version", value=algorithm["version"], key=f"d23-version-{algorithm_id}")
            rename = st.form_submit_button("Save algorithm identity")
        if rename:
            try:
                adapter.update_identity(algorithm_id, name, version)
            except ValueError as error:
                st.error(str(error))
            else:
                st.rerun()

    answers = algorithm["answers"]
    active = adapter.active_field_ids(algorithm_id)
    pending = [field_id for field_id in active if not _complete(field_id, answers.get(field_id, {}))]
    completed = len(active) - len(pending)
    st.progress(completed / len(active), text=f"{completed}/{len(active)} applicable answers complete")

    revision = state.d23_answer_revision
    with st.expander("Review confirmed D2.3 answers"):
        if answers:
            st.json(answers)
        record = adapter.build_record(algorithm_id)
        for issue in record["validation_problems"]:
            st.write(f"{issue['id']} — {issue['problem']}")
        for flag in record["flags"]:
            st.write(f"{', '.join(flag['fields'])} — {flag['message']}")
        edit = st.selectbox(
            "Revise a confirmed answer",
            [None, *answers],
            format_func=lambda field_id: (
                f"{field_id} — {BY_ID[field_id]['label']}" if field_id else "Continue with next question"
            ),
            key=f"d23-revise-{algorithm_id}-{revision}",
        )

    field_id = edit or (pending[0] if pending else None)
    with st.chat_message("assistant"):
        if field_id is None:
            st.write(f"All applicable questions for {_identity(algorithm)} have been answered.")
            return
        definition = BY_ID[field_id]
        st.write(f"**{field_id}** · {definition['label']}")
        if definition["help"]:
            st.caption(definition["help"])

    existing = answers.get(field_id, {})
    current = existing.get("value")
    if field_id == "ACC-001" and field_id not in answers:
        current = _identity(algorithm) if algorithm["version"] else algorithm["name"]
    key = f"d23-answer-{algorithm_id}-{field_id}-{revision}"
    with st.chat_message("user"):
        value = _answer_input(definition, current, key)
        if needs_details(field_id, value):
            st.caption("An explanation is required for this answer.")
        details = st.text_area("Explanation", value=existing.get("details", ""), key=f"{key}-details")
        evidence = st.text_input(
            "Document evidence reference",
            value=existing.get("evidence", ""),
            key=f"{key}-evidence",
            help="Enter the supporting document ID, version, and page or section.",
        )
        if st.button("Confirm D2.3 answer", key=f"{key}-confirm"):
            try:
                adapter.save_answer(algorithm_id, field_id, value, details=details, evidence=evidence)
            except ValueError as error:
                st.error(str(error))
            else:
                state.d23_answer_revision += 1
                st.rerun()
