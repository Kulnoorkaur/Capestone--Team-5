"""Record-scoped extraction and deterministic controls for D2.4 answers."""

import streamlit as st

from app.chatbot.chat_navigation import render_section_footer
from app.chatbot.chat_llm import extract_d24_candidates
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
    if picker_key not in st.session_state and adapter.selected_record_id in ids:
        st.session_state[picker_key] = adapter.selected_record_id

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
            st.session_state.d24_conversations.pop(record_id, None)
            st.rerun()
    return record_id


def _answer_input(field, current, key):
    if field.kind == "text":
        return st.text_area("Draft answer", value=current or "", key=key)
    if field.kind == "select":
        index = field.options.index(current) if current in field.options else None
        return st.selectbox("Draft answer", field.options, index=index, key=key)
    return st.multiselect("Draft answer", field.options, default=current or [], key=key)


def _reconcile_suggestions(adapter, record_id, conversation):
    pending = conversation["pending"]
    reachable = adapter.reachable_suggestions(record_id, {
        field_id: candidate["value"] for field_id, candidate in pending.items()
    })
    conversation["pending"] = {field_id: pending[field_id] for field_id in reachable}


def _render_extraction(adapter, record_id, scope, target, conversation):
    for message in conversation["turns"][-3:]:
        with st.chat_message("user"):
            st.text(message)
    if conversation["notice"]:
        st.info(conversation["notice"])
    if conversation["pending"]:
        st.caption("A new message replaces unconfirmed suggestions for this record.")
    message = st.chat_input(
        "Describe the selected record or answer the current question",
        key=f"d24-message-{record_id}", max_chars=8000,
    )
    if not message:
        return
    turns = conversation["turns"]
    source_id = str(len(turns) + 1)
    conversation["pending"] = {}
    labels = {}
    for kind, (_, name_field) in _RECORDS.items():
        for other_id in adapter.record_ids(kind):
            labels[other_id] = adapter.get_answers(other_id).get(name_field, "")
    try:
        with st.spinner("Reviewing your message…"):
            suggestions, clarification = extract_d24_candidates(
                message, record_id=record_id, scope=scope,
                record_label=labels.get(record_id) or ("Profile-wide GMLP" if scope == adapter.GMLP else record_id),
                source_id=source_id, fields=adapter.field_variants(record_id),
                active_fields=adapter.active_fields(record_id), target_field=target,
                confirmed=adapter.get_answers(record_id),
                other_labels=tuple(label for other_id, name in labels.items() if other_id != record_id
                                   for label in (other_id, name)),
                previous=tuple(turns[-6:]),
            )
    except Exception:
        conversation["notice"] = "Gemini could not process this message. You can continue with the manual controls."
    else:
        conversation["pending"] = suggestions
        _reconcile_suggestions(adapter, record_id, conversation)
        conversation["notice"] = clarification or (
            "" if suggestions and conversation["pending"]
            else "I couldn't verify an answer for this record. Please clarify or use the manual controls."
        )
    turns.append(message)
    st.rerun()


def _render_suggestions(adapter, record_id, active, revision, conversation):
    _reconcile_suggestions(adapter, record_id, conversation)
    for field_id, candidate in conversation["pending"].items():
        if field_id not in active:
            continue
        field = active[field_id]
        key = f"d24-review-{record_id}-{candidate['source_id']}-{field_id}-{revision}"
        with st.expander(f"Review suggestion for {field_id}", expanded=True):
            st.write(field.prompt)
            st.caption(f"User quotation · turn {candidate['source_id']}")
            st.text(candidate["quote"])
            if candidate["explanation"]:
                st.caption("Gemini explanation · not document evidence")
                st.text(candidate["explanation"])
            draft = _answer_input(field, candidate["value"], key)
            confirm, reject = st.columns(2)
            if confirm.button("Confirm suggestion", key=f"{key}-confirm"):
                try:
                    adapter.save_answer(record_id, field_id, draft)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state.d24_revisions[record_id] = revision + 1
                    st.rerun()
            if reject.button("Reject suggestion", key=f"{key}-reject"):
                conversation["pending"].pop(field_id)
                st.rerun()


def _render_record(adapter, record_id, scope):
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
        st.write(field.prompt)
    key = f"d24-answer-{record_id}-{field_id}-{revision}"
    conversation = st.session_state.d24_conversations.setdefault(
        record_id, {"turns": [], "pending": {}, "notice": ""},
    )
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
    _render_extraction(adapter, record_id, scope, field_id, conversation)
    _render_suggestions(adapter, record_id, active, revision, conversation)


def _required_findings(findings):
    return [issue for issue in findings if issue["type"] in ("missing", "conditional")]


def _resume_target(adapter, kind, record_id):
    scopes = [*((scope, adapter.record_ids(scope)) for scope in _RECORDS), (adapter.GMLP, (adapter.GMLP,))]
    targets = [(scope, identity) for scope, ids in scopes for identity in (ids or (None,))]
    selected = (kind, record_id)
    if selected in targets:
        targets.remove(selected)
        targets.insert(0, selected)
    for scope, identity in targets:
        if identity is None:
            return scope, None, None
        findings = _required_findings(adapter.validate_record(identity))
        if findings:
            fields = adapter.active_fields(identity)
            answers = adapter.get_answers(identity)
            field_id = next((
                field for issue in findings for field in fields
                if field not in answers and (
                    field == issue["field_id"] or field.startswith((f"{issue['field_id']}.", f"{issue['field_id']}-"))
                )
            ), None)
            return scope, identity, field_id
    return kind, record_id, None


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
    state.setdefault("d24_conversations", {})
    labels = {kind: label for kind, (label, _) in _RECORDS.items()}
    labels[adapter.GMLP] = "Profile-wide GMLP"
    if "d24-section" not in state and state.get("d24_active_scope") in labels:
        state["d24-section"] = state.d24_active_scope
    resume = state.pop("ux_resume_dataset", None)
    if resume:
        scope, identity, field = resume
        if identity is None or identity == adapter.GMLP or identity in adapter.record_ids(scope):
            state["d24-section"] = scope
            if identity is not None:
                if scope != adapter.GMLP:
                    state[f"d24-picker-{scope}"] = identity
                if field in adapter.active_fields(identity):
                    revision = state.d24_revisions.get(identity, 0)
                    state[f"d24-question-{identity}-{revision}"] = field
    kind = st.radio("Dataset and evidence section", tuple(labels), format_func=labels.get, key="d24-section")
    state.d24_active_scope = kind
    if kind == adapter.GMLP:
        record_id = adapter.GMLP
        adapter.select_record(record_id)
    else:
        record_id = _select_record(adapter, kind)
    if record_id is not None:
        _render_record(adapter, record_id, kind)
    gaps = _required_findings(adapter.validate())
    target = _resume_target(adapter, kind, record_id) if gaps else None
    hint = None
    if target:
        scope, identity, _ = target
        hint = f"Resume will open {labels[scope]}" + (f" ({identity})." if identity else " setup.")
    render_section_footer(
        "D2.4", [f"{issue['record']} · {issue['issue']}" for issue in gaps],
        context=f"d24-{state.get('ux_navigation_revision', 0)}-{kind}-{record_id}-{state.d24_revisions.get(record_id, 0)}",
        resume=lambda: state.update(ux_resume_dataset=target), resume_hint=hint,
    )
