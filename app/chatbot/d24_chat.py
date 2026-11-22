"""Record-scoped extraction and deterministic controls for D2.4 answers."""

import streamlit as st

from app.chatbot.chat_navigation import (
    conversational_question, keep_record_drafts, render_record_proposal,
    render_section_footer, unknown_option,
)
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
        st.session_state.pop("ux_d24_add", None)
        st.session_state.pop(f"ux_d24_proposal_{kind}", None)

    ids = adapter.record_ids(kind)
    if not ids:
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

    with st.expander(f"Remove {label.lower()}"):
        confirmed = st.checkbox(f"Remove {label_for(record_id)} and its answers", key=f"d24-remove-{record_id}")
        if st.button("Confirm removal", key=f"d24-delete-{record_id}", disabled=not confirmed) and confirmed:
            adapter.remove_record(record_id)
            st.session_state.d24_revisions.pop(record_id, None)
            st.session_state.d24_conversations.pop(record_id, None)
            st.session_state.get("ux_d24_introductions", {}).pop(record_id, None)
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
    if conversation["pending"]:
        st.caption("A new message replaces unconfirmed suggestions for this record.")
    message = st.chat_input(
        "Describe the selected record or answer the current question",
        key=f"d24-message-{record_id}", max_chars=8000,
    )
    if not message:
        return
    _submit_record_turn(adapter, record_id, scope, target, conversation, message)
    st.rerun()


def _record_conversation(conversations, record_id):
    return conversations.setdefault(record_id, {"turns": [], "pending": {}, "notice": ""})


def _submit_record_turn(adapter, record_id, scope, target, conversation, message, *, initial=False):
    turns = conversation["turns"]
    source_id = str(len(turns) + 1)
    previous = tuple(turns[-6:])
    turns.append(message)
    conversation["notice_target"] = None if initial else target
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
                previous=previous,
            )
    except Exception:
        conversation["notice"] = "Gemini could not process this message. You can continue with the manual controls."
    else:
        conversation["pending"] = suggestions
        _reconcile_suggestions(adapter, record_id, conversation)
        conversation["notice"] = clarification or (
            "" if initial or (suggestions and conversation["pending"])
            else "I couldn't verify an answer for this record. Please clarify or use the manual controls."
        )


def _render_suggestions(adapter, record_id, active, revision, conversation):
    _reconcile_suggestions(adapter, record_id, conversation)
    st.info("Review the extracted information. You can edit or reject each suggestion. Confirm only answers that are accurate.")
    for field_id, candidate in conversation["pending"].items():
        if field_id not in active:
            continue
        field = active[field_id]
        key = f"d24-review-{record_id}-{candidate['source_id']}-{field_id}-{revision}"
        with st.expander(conversational_question(field.prompt), expanded=True):
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
                    conversation.setdefault("skipped", set()).discard(field_id)
                    st.session_state.d24_revisions[record_id] = revision + 1
                    st.rerun()
            if reject.button("Reject suggestion", key=f"{key}-reject"):
                conversation["pending"].pop(field_id)
                st.rerun()


def _next_required_field(active, answers, findings, skipped=()):
    candidates = [field for field in active if field not in answers and field not in skipped]
    for issue in findings:
        field_id = issue["field_id"]
        for field in candidates:
            if field == field_id or field.startswith((f"{field_id}.", f"{field_id}-")):
                return field
    return None


def _manual_record_answers(adapter, record_id, active, answers, conversation, findings, target):
    if answers:
        st.json(answers)
    inactive = [field_id for field_id in adapter.field_ids(record_id) if field_id not in active]
    if inactive:
        st.caption("Inactive fields: " + ", ".join(inactive))
    if findings:
        st.dataframe([{"Field": item["field_id"], "Finding": item["issue"], "Status": item["type"]}
                      for item in findings], hide_index=True)
    revision = st.session_state.d24_revisions.get(record_id, 0)
    fields = tuple(active)
    field_id = st.selectbox(
        "Question to answer or edit", fields, index=fields.index(target) if target else 0,
        format_func=lambda item: f"{item} · {'Confirmed' if item in answers else 'Unanswered'}",
        key=f"d24-question-{record_id}-{revision}",
    )
    if field_id is None:
        return
    key = f"d24-answer-{record_id}-{field_id}-{revision}"
    draft = _answer_input(active[field_id], answers.get(field_id), key)
    if st.button("Confirm D2.4 answer", key=f"{key}-confirm"):
        try:
            adapter.save_answer(record_id, field_id, draft)
        except ValueError as error:
            st.error(str(error))
        else:
            conversation["skipped"].discard(field_id)
            st.session_state.d24_revisions[record_id] = revision + 1
            st.rerun()


def _question_actions(adapter, record_id, field_id, field, conversation, revision):
    unknown = unknown_option(field.kind, field.options)
    key = f"d24-action-{record_id}-{field_id}-{revision}"
    if unknown is not None and st.button("I don't know", key=f"{key}-unknown"):
        conversation["unknown_field"] = field_id
    if st.button("Skip for now", key=f"{key}-skip"):
        conversation["skipped"].add(field_id)
        conversation.pop("unknown_field", None)
        st.session_state.d24_revisions[record_id] = revision + 1
        st.rerun()
    if unknown is not None and conversation.get("unknown_field") == field_id:
        st.caption("Save Unknown as your confirmed answer.")
        if st.button("Confirm Unknown", key=f"{key}-confirm"):
            adapter.save_answer(record_id, field_id, unknown)
            conversation.pop("unknown_field", None)
            st.session_state.d24_revisions[record_id] = revision + 1
            st.rerun()


def _render_record(adapter, record_id, scope, tools):
    active = adapter.active_fields(record_id)
    answers = adapter.get_answers(record_id)
    findings = adapter.validate_record(record_id)
    required = _required_findings(findings)
    revision = st.session_state.d24_revisions.get(record_id, 0)
    conversation = _record_conversation(st.session_state.d24_conversations, record_id)
    skipped = conversation.setdefault("skipped", set())
    skipped.intersection_update(set(active) - answers.keys())
    target = _next_required_field(active, answers, required, skipped)
    if scope == adapter.GMLP and "DEP-036-trigger" not in answers and "DEP-036-trigger" not in skipped:
        target = "DEP-036-trigger"

    label, name_field = _RECORDS.get(scope, ("Profile-wide GMLP", None))
    st.caption(f"{answers.get(name_field, label)} · {len(answers)} confirmed · {len(required)} validation gaps")
    introduction = st.session_state.get("ux_d24_introductions", {}).get(record_id)
    for message in ([introduction] if introduction else []) + conversation["turns"]:
        with st.chat_message("user"):
            st.text(message)
    same_target = target is not None and conversation.get("notice_target") == target
    if conversation["notice"] and (same_target or conversation.get("notice_target") is None):
        with st.chat_message("assistant"):
            st.info(conversation["notice"])
    _reconcile_suggestions(adapter, record_id, conversation)
    reviewing = any(field_id in active for field_id in conversation["pending"])
    if reviewing:
        _render_suggestions(adapter, record_id, active, revision, conversation)
    elif target:
        with st.chat_message("assistant"):
            question = conversational_question(active[target].prompt)
            if same_target:
                st.write(f"To continue, please clarify this detail for the selected record. {question}")
            else:
                st.write(question)
        _question_actions(adapter, record_id, target, active[target], conversation, revision)
    elif required:
        with st.chat_message("assistant"):
            st.write("This record has unresolved information. Resume unanswered questions or review the technical controls.")
    else:
        with st.chat_message("assistant"):
            st.write(f"Required answers for this {label.lower()} are complete.")
    if skipped:
        st.caption(f"{len(skipped)} deferred questions for this record.")
    _render_extraction(adapter, record_id, scope, target, conversation)

    with tools:
        _manual_record_answers(adapter, record_id, active, answers, conversation, findings, target)
    return not reviewing and target is None


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


def _render_scope_actions(adapter, kind, record_id, labels, at_boundary):
    state = st.session_state
    if kind != adapter.GMLP and len(adapter.record_ids(kind)) > 1:
        with st.popover("Switch record"):
            for other_id in adapter.record_ids(kind):
                label = adapter.get_answers(other_id).get(_RECORDS[kind][1], other_id)
                if other_id != record_id and st.button(
                    f"Resume {label}", key=f"ux-d24-switch-{record_id}-{other_id}",
                ):
                    state["ux_resume_dataset"] = (kind, other_id, None)
                    st.rerun()
    if kind != adapter.GMLP and record_id and st.button(
        f"Describe another {labels[kind].lower()}", key=f"ux-d24-add-{record_id}",
    ):
        keep_record_drafts(state.d24_conversations, record_id, None, "d24-review-", "d24-answer-")
        state.ux_d24_add = kind
        st.rerun()
    if at_boundary:
        scopes = (*_RECORDS, adapter.GMLP)
        index = scopes.index(kind)
        if index + 1 < len(scopes):
            next_scope = scopes[index + 1]
            records = adapter.record_ids(kind)
            has_gaps = not records or any(_required_findings(adapter.validate_record(item)) for item in records)
            suffix = " with gaps" if has_gaps else ""
            if st.button(f"Continue to {labels[next_scope].lower()}{suffix}", key=f"ux-d24-next-{kind}-{record_id}"):
                state["ux_resume_dataset"] = (next_scope, None, None)
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
    conversations = state.setdefault("d24_conversations", {})
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
                    conversations.get(identity, {}).get("skipped", set()).discard(field)
                    revision = state.d24_revisions.get(identity, 0)
                    state[f"d24-question-{identity}-{revision}"] = field

    chat = st.container()
    tools = st.expander("Manage records and answers", expanded=False)
    previous_id = adapter.selected_record_id
    with tools:
        kind = st.radio("Dataset and evidence section", tuple(labels), format_func=labels.get, key="d24-section")
        state.d24_active_scope = kind
        if kind == adapter.GMLP:
            record_id = adapter.GMLP
            adapter.select_record(record_id)
        else:
            record_id = _select_record(adapter, kind)

    with chat:
        if kind != adapter.GMLP and (record_id is None or state.get("ux_d24_add") == kind):
            if record_id is None:
                keep_record_drafts(conversations, previous_id, None, "d24-review-", "d24-answer-")
            if record_id and st.button("Return to current record", key=f"ux-d24-cancel-{kind}"):
                state.pop("ux_d24_add", None)
                state.pop(f"ux_d24_proposal_{kind}", None)
                st.rerun()
            question = (
                "Now let's document the datasets and evidence supporting your AI system. "
                "What dataset would you like to start with?"
                if kind == "dataset" else f"Which {labels[kind].lower()} would you like to document?"
            )
            proposed = render_record_proposal(f"ux_d24_proposal_{kind}", question, include_version=kind != "document")
            if proposed:
                name, _, introduction = proposed
                new_id = adapter.create_record(kind)
                adapter.save_answer(new_id, _RECORDS[kind][1], name)
                state["ux_resume_dataset"] = (kind, new_id, None)
                state.pop("ux_d24_add", None)
                conversation = _record_conversation(conversations, new_id)
                target = _next_required_field(
                    adapter.active_fields(new_id), adapter.get_answers(new_id),
                    _required_findings(adapter.validate_record(new_id)),
                )
                _submit_record_turn(adapter, new_id, kind, target, conversation, introduction, initial=True)
                st.rerun()
            if record_id is None:
                st.caption(f"Add a {labels[kind].lower()} to begin.")
            at_boundary = record_id is None
        else:
            keep_record_drafts(conversations, previous_id, record_id, "d24-review-", "d24-answer-")
            at_boundary = _render_record(adapter, record_id, kind, tools)
        _render_scope_actions(adapter, kind, record_id, labels, at_boundary)

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
