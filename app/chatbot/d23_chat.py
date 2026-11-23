"""Algorithm-scoped conversation and confirmation for D2.3."""

import re

import streamlit as st

from app.chatbot.chat_navigation import (
    conversational_question, keep_record_drafts, render_record_proposal, unknown_option,
)
from app.chatbot.d23_adapter import D23AnswerAdapter
from app.chatbot.chat_llm import extract_d23_candidates
from app.deliverable_2.questionnaires.algorithm_change_control import (
    BY_ID,
    FRAMEWORKS,
    LOCKED,
    is_blank,
    needs_details,
)


_QUESTIONS = {
    "ACC-001": "What name and version identify this algorithm or model release?",
    "ACC-002": "Which of the AI functions already described for this product does this algorithm implement?",
    "ACC-003": "What learning approach or technique does this algorithm use?",
    "ACC-004": "What model architecture does the algorithm use, and does it use one model or several?",
    "ACC-006": "Does the same input produce the same output when the software version is unchanged? "
               "If not, what causes the output to vary?",
    "ACC-010": "What triggers learning, what data does it use, and who or what approves a change before it takes effect?",
    "ACC-011": "What safeguards limit changes the algorithm learns or settings that sites can configure?",
    "ACC-016": "For each planned modification, what will change, what limits apply, "
               "and how do you expect performance to be affected?",
    "ACC-017": "Would any planned change affect the product's intended use, indications, users, "
               "population, inputs, outputs, or performance claims? If so, which confirmed profile entries would change?",
    "ACC-018": "Will retraining use data from a different source, site, device vendor, or population "
               "than the original? If so, which dataset record describes that data?",
    "ACC-019": "Do you have a documented plan that specifies each planned change and how you will verify it? "
               "If so, identify the document and framework, such as a predetermined change control plan (PCCP).",
    "ACC-020": "Where does your algorithm's change-control plan stand with Health Canada, FDA, EU MDR "
               "(Medical Device Regulation), and the EU AI Act? For each framework, tell me whether it has "
               "been submitted, is planned for submission, is under review, has been authorized or accepted, "
               "or if another status applies.",
    "ACC-021": "Is there a documented procedure for controlling software and algorithm changes "
               "within your quality management system (QMS)? If so, provide its ID and version.",
    "ACC-029": "What changes, if any, have you made since the last regulatory authorization or first release?",
}


def _question(field_id):
    return _QUESTIONS.get(field_id) or conversational_question(BY_ID[field_id]["label"])


def _identity(record):
    return f"{record['name']} — {record['version'] or 'version not provided'}"


def _complete(field_id, answer):
    value = answer.get("value")
    return not is_blank(BY_ID[field_id]["type"], value) and (
        not needs_details(field_id, value) or bool(answer["details"].strip())
    )


def _unknown(value):
    selections = value.values() if isinstance(value, dict) else value if isinstance(value, list) else (value,)
    return "Unknown" in selections


def _deployment_conflict(values):
    if values.get("ACC-008") != LOCKED:
        return set()
    fields = set()
    if values.get("ACC-007") in ("Configurable by site or user", "Adjusted automatically"):
        fields.add("ACC-007")
    if set(values.get("ACC-009") or ()) - {"None", "Unknown"}:
        fields.add("ACC-009")
    return fields | {"ACC-008"} if fields else set()


_CONFLICT_QUESTION = (
    "You described the deployed model as locked, but also described settings or components that can change. "
    "Can they change at a site without a new manufacturer release, or only between releases?"
)


def d23_section_gaps():
    adapter = st.session_state.d23_adapter
    if not adapter.algorithm_ids:
        return ["Describe at least one algorithm."], None
    incomplete = []
    gaps = []
    for algorithm_id in adapter.algorithm_ids:
        problems = adapter.build_record(algorithm_id)["validation_problems"]
        algorithm = adapter.get_algorithm(algorithm_id)
        name = _identity(algorithm)
        active = adapter.active_field_ids(algorithm_id)
        answers = algorithm["answers"]
        unknowns = [field for field in active if _unknown(answers.get(field, {}).get("value"))]
        conflict = _deployment_conflict({field: answer["value"] for field, answer in answers.items()})
        if problems or unknowns or conflict:
            incomplete.append(algorithm_id)
        gaps.extend(
            f"{name} · {_question(field)} · Recorded as Unknown. Supporting information remains unresolved."
            for field in unknowns
        )
        if conflict:
            gaps.append(f"{name} · {_CONFLICT_QUESTION}")
        gaps.extend(f"{name} · {_question(issue['id'])} · {issue['problem']}"
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


def _submit_turn(adapter, conversation, algorithm_id, field_id, message, *, initial=False, question=None):
    algorithm = adapter.get_algorithm(algorithm_id)
    active = adapter.active_field_ids(algorithm_id)
    other_names = [
        adapter.get_algorithm(other_id)["name"]
        for other_id in adapter.algorithm_ids if other_id != algorithm_id
    ]
    conversation["turns"].append(message)
    source_id = str(len(conversation["turns"]))
    if question:
        conversation.setdefault("questions", {})[source_id] = question
    conversation["notice_target"] = None if initial else field_id
    conversation["request_failed"] = False
    bridge = st.session_state.get("questionnaire_bridge")
    d22_answers = bridge.get_questionnaire_answers("D2.2") if bridge else {}
    pending = conversation["candidates"].get(field_id)
    framework_followup = pending and pending.get("unresolved_frameworks")
    followup = pending if pending and not framework_followup and _missing_details(field_id, pending) else None
    existing = algorithm["answers"].get(field_id)
    if existing and not pending and not _complete(field_id, existing) and needs_details(field_id, existing["value"]):
        followup = {
            "algorithm_id": algorithm_id, "field_id": field_id, "source_id": source_id,
            "value": existing["value"], "details": existing["details"],
            "quote": algorithm["source_quotes"].get(field_id) or message, "correction": False,
        }
    try:
        suggestions, clarification = extract_d23_candidates(
            message, algorithm_id=algorithm_id, algorithm=algorithm, source_id=source_id,
            active_fields=active, target_field=field_id,
            other_algorithm_names=other_names,
            d22_answers=d22_answers,
            d21_answers=bridge.get_questionnaire_answers("D2.1") if bridge else {},
            d22_labels={key: bridge.get_field_label(key) for key in d22_answers},
            detail_followup=followup,
            original_reply=conversation["turns"][int(pending["source_id"]) - 1] if pending and followup else None,
        )
    except Exception:
        conversation["request_failed"] = True
        conversation["notice"] = "Gemini could not process that answer. Your message is retained. You can answer using the controls below."
        return
    if framework_followup and field_id in suggestions and not suggestions[field_id]["correction"]:
        updated = suggestions[field_id]
        additions = {key: status for key, status in updated["value"].items() if key in framework_followup}
        if additions:
            suggestions[field_id] = {
                **pending, "value": {**pending["value"], **additions},
                "details": " ".join(filter(None, (pending["details"], updated["quote"]))),
                "detail_source_id": source_id,
                "unresolved_frameworks": [key for key in framework_followup if key not in additions],
            }
        else:
            suggestions.pop(field_id)
    if existing and field_id == "ACC-020" and field_id in suggestions and not suggestions[field_id]["correction"]:
        candidate = suggestions[field_id]
        previous_statuses = {key: status for key, status in existing["value"].items() if status is not None}
        candidate["value"] = {**candidate["value"], **previous_statuses}
        candidate["unresolved_frameworks"] = [key for key in candidate.get("unresolved_frameworks", ())
                                              if key not in previous_statuses]
        candidate["details"] = " ".join(filter(None, (existing["details"], candidate["details"])))
    confirmed_values = {field: answer["value"] for field, answer in algorithm["answers"].items()}
    prospective = {**confirmed_values, **{field: item["value"] for field, item in suggestions.items()}}
    conflict = _deployment_conflict(prospective)
    conflicted = {
        field for field in conflict & suggestions.keys()
        if _deployment_conflict({**confirmed_values, field: suggestions[field]["value"]})
        or field not in confirmed_values
    }
    if conflicted:
        for field in conflicted:
            suggestions.pop(field)
            conversation["candidates"].pop(field, None)
        conversation["conflict_target"] = next(field for field in BY_ID if field in conflicted)
        clarification = _CONFLICT_QUESTION
    elif field_id in suggestions or any(item["correction"] for item in suggestions.values()):
        conversation.pop("conflict_target", None)
    for field, candidate in suggestions.items():
        rejected = conversation["rejected"].get(field, ())
        details = _evidence_key(candidate["details"])
        if any(
            _evidence_key(message) == prior_message
            or (not candidate["correction"] and _evidence_key(candidate["quote"]) == prior_quote
                and (not details or details in prior_message))
            for prior_message, prior_quote in rejected
        ):
            continue
        conversation["candidates"][field] = candidate
    if (followup or framework_followup) and field_id not in suggestions:
        conversation["notice"] = clarification or (
            "I kept the information you already supplied. You can fill the remaining detail directly "
            "in the review card below."
        )
    else:
        conversation["notice"] = clarification or (
            "" if suggestions or initial else "I couldn't identify a supported answer in that message."
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
            if not conversation["notice"]:
                conversation["notice"] = "A proposed answer did not meet the questionnaire requirements."
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
    if conversation.get("notice_target") == field_id:
        conversation["notice"] = ""
        conversation["notice_target"] = None
        conversation["request_failed"] = False
    st.session_state.d23_answer_revision += 1
    st.rerun()


def _dismiss_candidate(conversation, field_id, candidate, *, skip=False):
    source_id = candidate.get("detail_source_id", candidate["source_id"])
    message = conversation["turns"][int(source_id) - 1]
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


def _missing_details(field_id, candidate):
    return bool(candidate.get("unresolved_frameworks")) or needs_details(field_id, candidate["value"]) and (
        not candidate["details"].strip() or bool(candidate.get("missing_detail"))
    )


def _detail_question(field_id, candidate):
    if frameworks := candidate.get("unresolved_frameworks"):
        return f"Which status applies to the change plan for {', '.join(frameworks)}? You can reply in chat or select a status below."
    if candidate.get("missing_detail"):
        return candidate["missing_detail"]
    value = candidate["value"]
    label = BY_ID[field_id]["label"]
    detail = re.search(rf"\(if {re.escape(str(value))}: ([^()]*)\)", label, re.I)
    if detail:
        return f"What can you share about the {detail[1]}?"
    if value == "Unknown" or isinstance(value, list) and "Unknown" in value:
        return "What is still unknown, and why?"
    return "What details support this answer?"


def _render_reference_context(value):
    bridge = st.session_state.get("questionnaire_bridge")
    answers = bridge.get_product_profile() if bridge else {}
    for field in dict.fromkeys(re.findall(r"\b(?:PIP|AIF)-\d{3}(?:-[A-Z]+)?\b", value)):
        if field in answers:
            answer = answers[field]
            description = ", ".join(answer) if isinstance(answer, list) else answer
            st.caption(f"{field} · {bridge.get_field_label(field)}")
            st.text(description)
        else:
            st.caption(f"{field} · No confirmed profile answer for this reference.")


def _render_suggestions(adapter, algorithm_id, algorithm, conversation, suggestions, detail_target):
    st.subheader("Review extracted D2.3 answers")
    st.info("Review the extracted information. You can edit or reject each suggestion. Confirm only answers that are accurate.")
    for field_id, candidate in suggestions.items():
        definition = BY_ID[field_id]
        review_source = candidate.get("detail_source_id", candidate["source_id"])
        key = f"d23-review-{algorithm_id}-{review_source}-{field_id}"
        with st.expander(_question(field_id), expanded=True):
            st.text(_identity(algorithm))
            st.text(f"Source turn {candidate['source_id']}: {candidate['quote']}")
            value = _answer_input(definition, candidate["value"], key)
            if field_id == "ACC-002":
                _render_reference_context(value)
            if "detail_source_id" in candidate:
                st.caption(f"Explanation supplied in follow-up turn {candidate['detail_source_id']}.")
            existing = algorithm["answers"].get(field_id, {})
            details, evidence = _answer_metadata(
                field_id, value, key, details=candidate["details"], evidence=existing.get("evidence", ""),
            )
            if field_id == "ACC-017":
                _render_reference_context(details)
            if field_id == detail_target:
                if not details.strip():
                    st.caption("I couldn't verify an explanation. Add it in chat or edit it here.")
                else:
                    st.caption("You can add the missing detail in chat or edit the explanation here.")
                st.write(_detail_question(field_id, candidate))
            elif needs_details(field_id, value) and not details.strip():
                st.caption("Add an explanation before confirming.")
            confirm, reject, skip = st.columns(3)
            if confirm.button("Confirm suggestion", key=f"{key}-confirm"):
                quote = candidate["quote"] if _same_value(value, candidate["value"]) else ""
                try:
                    if needs_details(field_id, value) and not details.strip():
                        subject = "the component explanation" if field_id == "ACC-005" else "an explanation"
                        raise ValueError(f"Enter {subject} before confirming, or skip this suggestion for now.")
                    if candidate.get("missing_detail") and details.strip() == candidate["details"].strip():
                        raise ValueError("Supply the requested information or skip this suggestion for now.")
                    values = {field: answer["value"] for field, answer in algorithm["answers"].items()}
                    if field_id in _deployment_conflict({**values, field_id: value}):
                        raise ValueError(_CONFLICT_QUESTION)
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
    tools = st.expander("Manage algorithms and answers", expanded=state.get("d23_show_manual", False))
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
        st.progress(completed / len(active), text=f"{completed}/{len(active)} applicable responses recorded")
        findings = [item["message"] for item in adapter.build_record(algorithm_id)["flags"]
                    if item["severity"] in {"blocking", "gap"}]
        if findings:
            with st.expander(f"Review regulatory findings ({len(findings)})"):
                for finding in findings:
                    st.write(finding)
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
        if introduction:
            with st.chat_message("user"):
                st.text(introduction)
        questions = conversation.get("questions", {})
        for number, message in enumerate(conversation["turns"], 1):
            if question := questions.get(str(number)):
                with st.chat_message("assistant"):
                    st.text(question)
            with st.chat_message("user"):
                st.text(message)
        detail_target = next((field for field, candidate in suggestions.items()
                              if _missing_details(field, candidate)), None)
        conflict_target = conversation.get("conflict_target")
        if conflict_target not in active:
            conflict_target = None
        current = detail_target or conflict_target or target
        same_target = current is not None and conversation.get("notice_target") == current
        notice = conversation["notice"] if same_target or conversation.get("notice_target") is None else ""
        if notice and (not detail_target or conversation.get("request_failed")
                       or notice.startswith("I kept the information")):
            with st.chat_message("assistant"):
                st.write(notice)
        question = None
        if suggestions:
            _render_suggestions(adapter, algorithm_id, algorithm, conversation, suggestions, detail_target)
            if detail_target:
                question = _detail_question(detail_target, suggestions[detail_target])
        elif conflict_target:
            question = _CONFLICT_QUESTION
            if notice != question:
                with st.chat_message("assistant"):
                    st.write(question)
            if st.button("Set this clarification aside", key=f"d23-conflict-skip-{algorithm_id}"):
                conversation.pop("conflict_target", None)
                conversation["notice"] = ""
                st.rerun()
        elif target:
            question = _question(target)
            existing = algorithm["answers"].get(target)
            if existing and target == "ACC-020":
                missing = [name for name in FRAMEWORKS if not (existing["value"] or {}).get(name)]
                if missing:
                    question = f"What is the change-plan status for {', '.join(missing)}?"
            elif existing and needs_details(target, existing["value"]):
                question = _detail_question(target, existing)
            if same_target and target == "ACC-002":
                question = ("Which confirmed AI-function entries describe what this algorithm implements? "
                            "You can describe the matching capability in your own words.")
            elif same_target and target == "ACC-020":
                question = "Choose a listed status for each framework you can confirm, or tell me the status in chat."
            elif same_target and "?" in notice:
                question = notice
            elif same_target:
                options = BY_ID[target]["options"]
                if BY_ID[target]["type"] == "select" and 1 < len(options) <= 4:
                    question = f"Which answer fits best: {', '.join(options)}? You can add context in your own words."
                else:
                    question = "You can clarify your answer in chat, edit it manually, or skip for now."
            with st.chat_message("assistant"):
                if question != notice:
                    st.write(question)
                if target == "ACC-020" and same_target:
                    st.caption("Available statuses: " + " · ".join(BY_ID[target]["options"]))
                context_ref = {"ACC-001": "PIP-001", "ACC-007": "AIF-009"}.get(target)
                bridge = state.get("questionnaire_bridge")
                if context_ref and bridge and context_ref in bridge.answers:
                    st.caption(f"Previously confirmed · {bridge.get_field_label(context_ref)}")
                    st.write(bridge.answers[context_ref])
            if bridge and target in {"ACC-002", "ACC-017"}:
                entries = bridge.get_questionnaire_answers("D2.2")
                if target == "ACC-017":
                    entries = {**bridge.get_questionnaire_answers("D2.1"), **entries}
                if entries:
                    with st.expander("Review previously confirmed profile information"):
                        for field, answer in entries.items():
                            st.caption(bridge.get_field_label(field))
                            st.write(", ".join(answer) if isinstance(answer, list) else answer)
            if same_target and st.button("Edit this answer manually", key=f"d23-manual-{algorithm_id}-{target}"):
                state.d23_show_manual = True
                st.rerun()
            _question_actions(adapter, algorithm_id, target, conversation)
        elif adapter.build_record(algorithm_id)["validation_problems"]:
            with st.chat_message("assistant"):
                st.write("This algorithm still has questions to resolve. Use the gap summary to resume.")
        else:
            with st.chat_message("assistant"):
                if any(_unknown(answer["value"]) for answer in algorithm["answers"].values()) or _deployment_conflict(
                    {field: answer["value"] for field, answer in algorithm["answers"].items()}
                ):
                    st.write("The required responses are recorded. Documentation gaps remain in the summary below.")
                else:
                    st.write(f"Required responses for {_identity(algorithm)} are recorded. This does not establish regulatory readiness.")
        message = st.chat_input(
            "Describe this algorithm or answer in your own words",
            key=f"d23-chat-input-{algorithm_id}", disabled=bool(suggestions) and detail_target is None,
        )
        if message and message.strip() and (not suggestions or detail_target):
            _submit_turn(adapter, conversation, algorithm_id, current, message, question=question)
            st.rerun()
    with tools:
        _manual_algorithm_answers(adapter, algorithm_id, algorithm, conversation, active, pending, target)
