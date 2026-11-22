"""Algorithm-scoped conversation and confirmation for D2.3."""

import streamlit as st

from app.chatbot.chat_navigation import (
    conversational_question, keep_record_drafts, render_record_proposal, unknown_option,
)
from app.chatbot.d23_adapter import D23AnswerAdapter
from app.chatbot.chat_llm import extract_d23_candidates
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


def d23_section_gaps():
    adapter = st.session_state.d23_adapter
    if not adapter.algorithm_ids:
        return ["Describe at least one algorithm."], None
    incomplete = []
    gaps = []
    for algorithm_id in adapter.algorithm_ids:
        problems = adapter.build_record(algorithm_id)["validation_problems"]
        if problems:
            incomplete.append(algorithm_id)
        name = _identity(adapter.get_algorithm(algorithm_id))
        gaps.extend(f"{name} · {conversational_question(BY_ID[issue['id']]['label'])} · {issue['problem']}"
                    for issue in problems)
    active_id = st.session_state.get("d23_active_algorithm_id")
    return gaps, active_id if active_id in incomplete else next(iter(incomplete), None)


def resume_d23(algorithm_id):
    if algorithm_id is None:
        return False
    state = st.session_state
    state["ux_resume_algorithm"] = algorithm_id
    state.d23_answer_revision += 1


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


def _answer_metadata(field_id, value, key, *, details="", evidence=""):
    if needs_details(field_id, value):
        st.caption("An explanation is required for this answer.")
    details = st.text_area("Explanation", value=details, key=f"{key}-details")
    evidence = st.text_input(
        "Document evidence reference", value=evidence, key=f"{key}-evidence",
        help="Enter the supporting document ID, version, and page or section.",
    )
    return details, evidence


def _evidence_key(value):
    return " ".join(value.casefold().split())


def _algorithm_conversation(conversations, algorithm_id):
    return conversations.setdefault(algorithm_id, {
        "turns": [], "candidates": {}, "rejected": {}, "skipped": set(), "notice": "",
    })


def _submit_turn(adapter, conversation, algorithm_id, field_id, message, *, initial=False):
    algorithm = adapter.get_algorithm(algorithm_id)
    active = adapter.active_field_ids(algorithm_id)
    other_names = [
        adapter.get_algorithm(other_id)["name"]
        for other_id in adapter.algorithm_ids if other_id != algorithm_id
    ]
    conversation["turns"].append(message)
    source_id = str(len(conversation["turns"]))
    try:
        suggestions, clarification = extract_d23_candidates(
            message, algorithm_id=algorithm_id, algorithm=algorithm, source_id=source_id,
            active_fields=active, target_field=field_id,
            other_algorithm_names=other_names,
        )
    except Exception:
        conversation["notice"] = "Gemini could not process that answer. Your message is retained. You can answer using the controls below."
        return
    for field, candidate in suggestions.items():
        rejected = conversation["rejected"].get(field, ())
        if any(
            _evidence_key(message) == prior_message
            or (not candidate["correction"] and _evidence_key(candidate["quote"]) == prior_quote)
            for prior_message, prior_quote in rejected
        ):
            continue
        conversation["candidates"][field] = candidate
    conversation["notice"] = clarification or (
        "" if suggestions or initial else "I couldn't identify a supported answer. Could you clarify the detail for this algorithm?"
    )


def _active_suggestions(adapter, algorithm_id, active, conversation):
    suggestions = {}
    candidates = conversation["candidates"]
    for field_id in active:
        candidate = candidates.get(field_id)
        if not candidate or candidate["algorithm_id"] != algorithm_id:
            continue
        try:
            adapter.check_answer(algorithm_id, field_id, candidate["value"], details=candidate["details"])
        except ValueError:
            candidates.pop(field_id)
        else:
            suggestions[field_id] = candidate
    return suggestions


def _save_answer(adapter, algorithm_id, field_id, value, details, evidence, conversation, quote=""):
    selections = value.values() if isinstance(value, dict) else value if isinstance(value, list) else (value,)
    if "Unknown" in selections and needs_details(field_id, value) and not details.strip():
        raise ValueError("Explain why the answer is unknown before confirming it.")
    active = set(adapter.active_field_ids(algorithm_id))
    adapter.save_answer(algorithm_id, field_id, value, details=details, evidence=evidence, source_quote=quote)
    obsolete = active - set(adapter.active_field_ids(algorithm_id)) | {field_id}
    for removed in obsolete:
        conversation["candidates"].pop(removed, None)
    conversation["skipped"].difference_update(obsolete)
    st.session_state.d23_answer_revision += 1
    st.rerun()


def _dismiss_candidate(conversation, field_id, candidate, *, skip=False):
    message = conversation["turns"][int(candidate["source_id"]) - 1]
    conversation["rejected"].setdefault(field_id, set()).add(
        (_evidence_key(message), _evidence_key(candidate["quote"]))
    )
    conversation["candidates"].pop(field_id)
    if skip:
        conversation["skipped"].add(field_id)
    st.rerun()


def _same_value(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        return {k: v for k, v in left.items() if v is not None} == {
            k: v for k, v in right.items() if v is not None
        }
    return left == right


def _render_suggestions(adapter, algorithm_id, algorithm, conversation, suggestions):
    st.subheader("Review extracted D2.3 answers")
    for field_id, candidate in suggestions.items():
        definition = BY_ID[field_id]
        key = f"d23-review-{algorithm_id}-{candidate['source_id']}-{field_id}"
        with st.expander(conversational_question(definition["label"]), expanded=True):
            st.text(_identity(algorithm))
            st.text(f"Source turn {candidate['source_id']}: {candidate['quote']}")
            value = _answer_input(definition, candidate["value"], key)
            details, evidence = _answer_metadata(field_id, value, key, details=candidate["details"])
            confirm, reject, skip = st.columns(3)
            if confirm.button("Confirm suggestion", key=f"{key}-confirm"):
                quote = candidate["quote"] if _same_value(value, candidate["value"]) else ""
                try:
                    _save_answer(adapter, algorithm_id, field_id, value, details, evidence, conversation, quote)
                except ValueError as error:
                    st.error(str(error))
            if reject.button("Reject suggestion", key=f"{key}-reject"):
                _dismiss_candidate(conversation, field_id, candidate)
            if skip.button("Skip suggestion", key=f"{key}-skip"):
                _dismiss_candidate(conversation, field_id, candidate, skip=True)


def _algorithm_tools(adapter, state):
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
            state.pop("ux_d23_add", None)
            state.pop("ux_d23_proposal", None)

    if not adapter.algorithm_ids:
        return None
    selected = state.pop("ux_select_algorithm", None)
    if selected in adapter.algorithm_ids:
        state["d23-algorithm-picker"] = selected
    resume = state.pop("ux_resume_algorithm", None)
    if resume in adapter.algorithm_ids:
        state["d23-algorithm-picker"] = resume
        skipped = state.d23_conversations.get(resume, {}).get("skipped")
        if skipped is not None:
            skipped.difference_update(issue["id"] for issue in adapter.build_record(resume)["validation_problems"])
    if "d23-algorithm-picker" not in state:
        active = state.get("d23_active_algorithm_id")
        if active in adapter.algorithm_ids:
            state["d23-algorithm-picker"] = active
    return st.selectbox(
        "Selected algorithm",
        adapter.algorithm_ids,
        index=None,
        format_func=lambda item: f"{_identity(adapter.get_algorithm(item))} ({item})",
        key="d23-algorithm-picker",
    )


def _manual_algorithm_answers(adapter, algorithm_id, algorithm, conversation, active, pending, target):
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
            if (name, version) != (algorithm["name"], algorithm["version"]):
                conversation["candidates"].clear()
                conversation["notice"] = ""
            st.rerun()

    answers = algorithm["answers"]
    if answers:
        st.json(answers)
    record = adapter.build_record(algorithm_id)
    for issue in record["validation_problems"]:
        st.write(f"{issue['id']} — {issue['problem']}")
    for flag in record["flags"]:
        st.write(f"{', '.join(flag['fields'])} — {flag['message']}")
    revision = st.session_state.d23_answer_revision
    editable = [field for field in active if field in answers or field in conversation["skipped"]]
    edit = st.selectbox(
        "Revise a confirmed or skipped answer", [None, *editable],
        format_func=lambda field_id: (
            f"{field_id} — {BY_ID[field_id]['label']}" if field_id else "Continue with next question"
        ),
        key=f"d23-revise-{algorithm_id}-{revision}",
    )
    field_id = edit or target
    if field_id is None:
        return
    definition = BY_ID[field_id]
    existing = answers.get(field_id, {})
    current = existing.get("value")
    if field_id == "ACC-001" and field_id not in answers:
        current = _identity(algorithm) if algorithm["version"] else algorithm["name"]
    key = f"d23-answer-{algorithm_id}-{field_id}-{revision}"
    value = _answer_input(definition, current, key)
    details, evidence = _answer_metadata(
        field_id, value, key, details=existing.get("details", ""), evidence=existing.get("evidence", ""),
    )
    if st.button("Confirm D2.3 answer", key=f"{key}-confirm"):
        quote = algorithm["source_quotes"].get(field_id, "") if _same_value(value, current) else ""
        try:
            _save_answer(adapter, algorithm_id, field_id, value, details, evidence, conversation, quote)
        except ValueError as error:
            st.error(str(error))
    if field_id in pending and st.button("Skip this question", key=f"{key}-skip"):
        conversation["skipped"].add(field_id)
        st.session_state.d23_answer_revision += 1
        st.rerun()


def _question_actions(adapter, algorithm_id, field_id, conversation):
    definition = BY_ID[field_id]
    unknown = unknown_option(definition["type"], definition["options"])
    key = f"d23-action-{algorithm_id}-{field_id}-{st.session_state.d23_answer_revision}"
    if unknown is not None and st.button("I don't know", key=f"{key}-unknown"):
        conversation["unknown_field"] = field_id
    if st.button("Skip for now", key=f"{key}-skip"):
        conversation["skipped"].add(field_id)
        conversation.pop("unknown_field", None)
        st.session_state.d23_answer_revision += 1
        st.rerun()
    if unknown is not None and conversation.get("unknown_field") == field_id:
        details = st.text_area("Why is this unknown?", key=f"{key}-details")
        if st.button("Confirm Unknown", key=f"{key}-confirm"):
            if needs_details(field_id, unknown) and not details.strip():
                st.error("Explain why the answer is unknown before confirming it.")
            else:
                conversation.pop("unknown_field", None)
                _save_answer(adapter, algorithm_id, field_id, unknown, details, "", conversation)


def render_d23_chat():
    state = st.session_state
    if "d23_adapter" not in state:
        state.d23_adapter = D23AnswerAdapter()
        state.d23_answer_revision = 0
    adapter = state.d23_adapter
    conversations = state.setdefault("d23_conversations", {})
    st.subheader("D2.3 — Algorithm Change Control")

    # Reserve the main conversation above the technical controls.
    chat = st.container()
    tools = st.expander("Manage algorithms and answers", expanded=False)
    with tools:
        algorithm_id = _algorithm_tools(adapter, state)

    with chat:
        if not algorithm_id and adapter.algorithm_ids and not state.get("ux_d23_add"):
            with st.chat_message("assistant"):
                st.write("Which algorithm would you like to resume?")
            for existing_id in adapter.algorithm_ids:
                if st.button(f"Resume {_identity(adapter.get_algorithm(existing_id))}",
                             key=f"ux-d23-resume-{existing_id}"):
                    state["ux_select_algorithm"] = existing_id
                    st.rerun()
            if st.button("Add another algorithm", key="ux-d23-add-existing"):
                state.ux_d23_add = True
                st.rerun()
            return
        if not algorithm_id or state.get("ux_d23_add"):
            if algorithm_id and st.button("Return to current algorithm", key="ux-d23-cancel-add"):
                state.pop("ux_d23_add", None)
                state.pop("ux_d23_proposal", None)
                st.rerun()
            proposed = render_record_proposal(
                "ux_d23_proposal", "Let's start by documenting your algorithm. What is its name and version?",
                algorithm=True,
            )
            if proposed:
                name, version, introduction = proposed
                new_id = adapter.add_algorithm(name, version)
                adapter.save_answer(new_id, "ACC-001", f"{name} {version}".strip())
                state["ux_select_algorithm"] = new_id
                state.pop("ux_d23_add", None)
                conversation = _algorithm_conversation(conversations, new_id)
                answers = adapter.get_algorithm(new_id)["answers"]
                target = next((field for field in adapter.active_field_ids(new_id) if field not in answers), None)
                _submit_turn(adapter, conversation, new_id, target, introduction, initial=True)
                st.rerun()
            return

    previous_id = state.get("d23_active_algorithm_id")
    keep_record_drafts(
        conversations, previous_id, algorithm_id, "d23-review-", "d23-answer-",
        revision=state.d23_answer_revision,
    )
    state.d23_active_algorithm_id = algorithm_id
    algorithm = adapter.get_algorithm(algorithm_id)
    conversation = _algorithm_conversation(conversations, algorithm_id)
    active = adapter.active_field_ids(algorithm_id)
    pending = [field for field in active if not _complete(field, algorithm["answers"].get(field, {}))]
    target = next((field for field in pending if field not in conversation["skipped"]), None)
    suggestions = _active_suggestions(adapter, algorithm_id, active, conversation)

    with chat:
        st.caption(f"Algorithm: {_identity(algorithm)}")
        completed = len(active) - len(pending)
        st.progress(completed / len(active), text=f"{completed}/{len(active)} applicable answers complete")
        if len(adapter.algorithm_ids) > 1:
            with st.popover("Switch algorithm"):
                for other_id in adapter.algorithm_ids:
                    if other_id != algorithm_id and st.button(
                        f"Resume {_identity(adapter.get_algorithm(other_id))}",
                        key=f"ux-d23-switch-{algorithm_id}-{other_id}",
                    ):
                        state["ux_select_algorithm"] = other_id
                        st.rerun()
        if st.button("Add another algorithm", key=f"ux-d23-add-{algorithm_id}"):
            keep_record_drafts(conversations, algorithm_id, None, "d23-review-", "d23-answer-")
            state.ux_d23_add = True
            st.rerun()
        introduction = state.get("ux_d23_introductions", {}).get(algorithm_id)
        for message in ([introduction] if introduction else []) + conversation["turns"]:
            with st.chat_message("user"):
                st.text(message)
        if conversation["notice"]:
            with st.chat_message("assistant"):
                st.write(conversation["notice"])
        if suggestions:
            _render_suggestions(adapter, algorithm_id, algorithm, conversation, suggestions)
        elif target:
            with st.chat_message("assistant"):
                st.write(conversational_question(BY_ID[target]["label"]))
            _question_actions(adapter, algorithm_id, target, conversation)
        elif adapter.build_record(algorithm_id)["validation_problems"]:
            with st.chat_message("assistant"):
                st.write("This algorithm still has questions to resolve. Use the gap summary to resume.")
        else:
            with st.chat_message("assistant"):
                st.write(f"Required answers for {_identity(algorithm)} are complete. You can add another algorithm or return to an existing one.")
        message = st.chat_input(
            "Describe this algorithm or answer in your own words",
            key=f"d23-chat-input-{algorithm_id}", disabled=bool(suggestions),
        )
        if message and message.strip() and not suggestions:
            _submit_turn(adapter, conversation, algorithm_id, target, message)
            st.rerun()
    with tools:
        _manual_algorithm_answers(adapter, algorithm_id, algorithm, conversation, active, pending, target)
