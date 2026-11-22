"""Deterministic Chat Buddy controls for confirmed D2.4 answers."""

import streamlit as st

from app.chatbot.d24_adapter import D24AnswerAdapter
from app.chatbot.d24_metadata import D24CompatibilityError


_RECORDS = {
    "dataset": ("Dataset", "DEP-001.dataset_name_version"),
    "function": ("AI function / version", "DEP-019-versions"),
    "document": ("Supporting document", "title"),
}


def _select_record(adapter, kind):
    label, name_field = _RECORDS[kind]
    picker_key = f"d24-picker-{kind}"
    if st.button(f"Add {label.lower()}", key=f"d24-add-{kind}"):
        st.session_state[picker_key] = adapter.create_record(kind)

    ids = adapter.record_ids(kind)
    if not ids:
        st.caption(f"Add a {label.lower()} to begin.")
        return None

    def label_for(record_id):
        name = adapter.get_answers(record_id).get(name_field)
        return f"{name or label} ({record_id})"

    record_id = st.selectbox(f"Selected {label.lower()}", ids, format_func=label_for, key=picker_key)
    if record_id is None:
        return None
    adapter.select_record(record_id)
    st.caption(f"Editing {label_for(record_id)}")

    with st.expander(f"Remove {label.lower()}"):
        confirmed = st.checkbox(f"Remove {label_for(record_id)} and its answers", key=f"d24-remove-{record_id}")
        if st.button("Confirm removal", key=f"d24-delete-{record_id}", disabled=not confirmed) and confirmed:
            adapter.remove_record(record_id)
            st.session_state.d24_revisions.pop(record_id, None)
            st.rerun()
    return record_id


def _answer_input(field, current, key):
    if field.kind == "text":
        return st.text_area("Draft answer", value=current or "", key=key)
    if field.kind == "select":
        index = field.options.index(current) if current in field.options else None
        return st.selectbox("Draft answer", field.options, index=index, key=key)
    return st.multiselect("Draft answer", field.options, default=current or [], key=key)


def _render_record(adapter, record_id):
    active = adapter.active_fields(record_id)
    answers = adapter.get_answers(record_id)
    unanswered = [field_id for field_id in active if field_id not in answers]
    inactive = [field_id for field_id in adapter.field_ids(record_id) if field_id not in active]
    st.caption(f"{len(answers)} confirmed · {len(unanswered)} unanswered · {len(inactive)} inactive")

    with st.expander("Review confirmed answers and validation findings"):
        if answers:
            st.json(answers)
        else:
            st.caption("No confirmed answers for this record.")
        if inactive:
            st.caption("Inactive fields: " + ", ".join(inactive))
        findings = adapter.validate_record(record_id)
        if findings:
            st.dataframe([{"Field": issue["field_id"], "Finding": issue["issue"], "Status": issue["type"]}
                          for issue in findings], hide_index=True)
        else:
            st.caption("No findings from the questionnaire validator.")

    revision = st.session_state.d24_revisions.get(record_id, 0)
    field_id = st.selectbox(
        "Question to answer or edit",
        tuple(active),
        index=tuple(active).index(unanswered[0]) if unanswered else 0,
        format_func=lambda item: f"{item} · {'Confirmed' if item in answers else 'Unanswered'}",
        key=f"d24-question-{record_id}-{revision}",
    )
    if field_id is None:
        return
    field = active[field_id]
    with st.chat_message("assistant"):
        st.write(f"**{field_id}**")
        st.write(field.prompt)
    key = f"d24-answer-{record_id}-{field_id}-{revision}"
    draft = _answer_input(field, answers.get(field_id), key)
    st.caption("Review your draft. It is saved only when you confirm it.")
    if st.button("Confirm D2.4 answer", key=f"{key}-confirm"):
        try:
            adapter.save_answer(record_id, field_id, draft)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state.d24_revisions[record_id] = revision + 1
            st.rerun()


def render_d24_chat():
    state = st.session_state
    st.subheader("D2.4 — Dataset and Evidence")
    try:
        if "d24_adapter" not in state:
            state.d24_adapter = D24AnswerAdapter()
        else:
            state.d24_adapter.check_compatibility()
    except D24CompatibilityError as error:
        st.error(str(error))
        st.caption("D2.4 editing is disabled. Existing confirmed answers are preserved.")
        return

    adapter = state.d24_adapter
    state.setdefault("d24_revisions", {})
    labels = {kind: label for kind, (label, _) in _RECORDS.items()}
    labels[adapter.GMLP] = "Profile-wide GMLP"
    kind = st.radio("Dataset and evidence section", tuple(labels), format_func=labels.get, key="d24-section")
    if kind == adapter.GMLP:
        record_id = adapter.GMLP
        adapter.select_record(record_id)
    else:
        record_id = _select_record(adapter, kind)
    if record_id is not None:
        _render_record(adapter, record_id)
