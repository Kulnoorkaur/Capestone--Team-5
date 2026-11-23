"""
AI Regulatory Readiness Platform
Gemini-Powered Chat Buddy — D2.1 and D2.2

Features:
- Natural-language product intake
- Gemini field extraction
- Developer confirmation
- Context-aware questions
- Reliable question progression
- Clarification of unanswered fields
- Conditional questionnaire fields
- Manual questionnaire editing
- JSON profile export
"""

import json
import streamlit as st

from app.chatbot.chat_llm import (
    extract_questionnaire_fields,
    generate_questionnaire_question,
    handle_user_clarification,
)

from app.chatbot.chat_navigation import render_section_footer
from app.chatbot.d23_chat import d23_response_progress, d23_section_gaps, render_d23_chat, render_d23_history, resume_d23
from app.chatbot.d24_adapter import D24AnswerAdapter
from app.chatbot.d24_chat import d24_progress_status, d24_response_progress, render_d24_chat
from app.chatbot.d24_metadata import D24CompatibilityError
from app.chatbot.profile_io import (
    CombinedProfile,
    ProfileImportError,
    dump_combined_profile,
    load_profile_upload,
)
from app.chatbot.questionnaire_bridge import CONDITIONAL_FIELDS, QuestionnaireBridge
from app.deliverable_2.validation.run_ai_function import validate_ai_function
from app.deliverable_3.product_validation import validate_profile


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Regulatory Readiness Platform",
    page_icon="💬",
    layout="wide",
)


WELCOME = (
    "Welcome! I'll help you build a regulatory readiness "
    "profile for your imaging AI product.\n\n"
    "To begin, describe your product, what it does, "
    "and who will use it."
)


# ============================================================
# SESSION STATE
# ============================================================

def new_carryover_state():
    return {
        "turns": {},
        "evidence": {},
        "confirmed_sources": set(),
        "rejected": {},
        "queued": {},
        "attempted": set(),
        "handoff_done": False,
    }


def initialize_session():

    defaults = {
        "questionnaire_bridge": QuestionnaireBridge,
        "unified_messages": lambda: [
            {
                "role": "assistant",
                "content": WELCOME,
            }
        ],
        "field_suggestions": dict,
        "carryover": new_carryover_state,
        "asked_field": lambda: None,
        "asked_question": lambda: None,
        "retryable_turn": lambda: None,
        "intake_started": lambda: False,
        "questionnaire_complete": lambda: False,
        "needs_next_question": lambda: False,
        "clarification_needed": lambda: False,
        "editor_version": lambda: 0,
        "review_batch_version": lambda: 0,
        "active_questionnaire": lambda: "D2.1",
    }

    for name, factory in defaults.items():

        if name not in st.session_state:
            st.session_state[name] = factory()


initialize_session()

bridge = st.session_state.questionnaire_bridge


# ============================================================
# CONVERSATION HELPERS
# ============================================================

def add_message(role, content):

    st.session_state.unified_messages.append(
        {
            "role": role,
            "content": content,
        }
    )


QUESTIONNAIRES = ("D2.1", "D2.2")
QUESTIONNAIRE_NAMES = {
    "D2.1": "Product and Intended-Use Profile",
    "D2.2": "AI Function and Clinical Workflow",
}


def questionnaire_for_field(field_id):
    if field_id and field_id.startswith("AIF-"):
        return "D2.2"
    return "D2.1"


def pending_fields(questionnaire):
    """Conditional fields first, followed by required primary fields."""
    return [
        field_id for field_id in (
            bridge.get_active_conditional_fields(questionnaire)
            + bridge.get_missing_fields(questionnaire)
        ) if field_id not in bridge.answers
    ]


def get_next_field():
    for questionnaire in QUESTIONNAIRES:
        pending = pending_fields(questionnaire)
        if pending:
            st.session_state.active_questionnaire = questionnaire
            return pending[0]
    return None


def fallback_question(field_id):

    label = bridge.get_field_label(field_id)

    options = bridge.get_field_options(field_id)

    question = (
        f"Could you provide information about "
        f"**{label}** for your product?"
    )

    if options:

        question += (
            "\n\nAvailable options: "
            + ", ".join(options)
        )

    return question


def ask_question(field_id, clarification=False):

    if field_id is None:

        st.session_state.asked_field = None
        st.session_state.asked_question = None
        st.session_state.needs_next_question = False

        st.session_state.questionnaire_complete = True

        return

    st.session_state.active_questionnaire = questionnaire_for_field(field_id)
    label = bridge.get_field_label(field_id)

    field_type = bridge.get_field_type(field_id)

    options = bridge.get_field_options(field_id)

    try:

        question = generate_questionnaire_question(
            field_id=field_id,
            field_label=label,
            field_type=field_type,
            field_options=options,
            confirmed_answers=bridge.get_product_profile(),
        )

    except Exception:

        question = fallback_question(field_id)

    if clarification:

        question = (
            f"I still need to confirm **{label}**.\n\n"
            f"{question}\n\n"
            "You can also answer this question "
            "using the Manual Questionnaire Editor."
        )

    st.session_state.asked_field = field_id

    st.session_state.asked_question = question

    st.session_state.questionnaire_complete = False

    st.session_state.needs_next_question = False

    st.session_state.clarification_needed = False

    add_message(
        "assistant",
        question,
    )


# ============================================================
# QUESTION PROGRESSION
# ============================================================

def schedule_next_question():

    """
    Mark the conversation as ready to continue.

    The actual question is generated on the next
    Streamlit rerun.
    """

    st.session_state.needs_next_question = True


def evidence_key(text):
    return " ".join(text.casefold().split())


def was_rejected(field_id, message, quote=None):
    source = evidence_key(message)
    excerpt = f" {evidence_key(quote)} " if quote else None
    return any(
        source == rejected_source or (excerpt is not None and excerpt in f" {rejected_quote} ")
        for rejected_source, rejected_quote in st.session_state.carryover["rejected"].get(field_id, ())
    )


def queue_activated_followups(field_id, value, active_before):
    state = st.session_state.carryover
    evidence = state["evidence"].pop(field_id, None)
    if not evidence or evidence["value"] != value:
        return
    source_id = evidence["source_id"]
    state["confirmed_sources"].add(source_id)
    questionnaire = questionnaire_for_field(field_id)
    source_text = evidence_key(state["turns"][source_id]["message"]).rstrip(".!?")
    selected_option = value[0] if isinstance(value, list) and len(value) == 1 else value
    if isinstance(selected_option, str) and source_text == evidence_key(selected_option):
        return
    for child_id in bridge.get_active_conditional_fields(questionnaire):
        if child_id not in active_before and CONDITIONAL_FIELDS[child_id][0] == field_id:
            state["queued"][child_id] = (source_id, value)


def open_carryover_review(questionnaire, field_sources, *, handoff=False):
    state = st.session_state.carryover
    source_ids = dict.fromkeys(
        source_id for sources in field_sources.values() for source_id in sources
    )
    sources = {}
    seen = set()
    for source_id in source_ids:
        turn = state["turns"][source_id]
        excerpt = turn["message"][:1800]
        key = (evidence_key(excerpt), turn["question"])
        if not key[0] or key in seen:
            continue
        seen.add(key)
        sources[source_id] = {
            "message": excerpt,
            "original_question": (turn["question"] or "")[:600],
        }
        if len(sources) == 6:
            break

    eligible = {
        field: [source_id for source_id in ids if source_id in sources]
        for field, ids in field_sources.items()
        if sources.keys() & set(ids)
    }
    if not eligible:
        return False

    try:
        candidates = extract_questionnaire_fields(
            user_message=None,
            confirmed_answers=bridge.get_product_profile(),
            questionnaire=questionnaire,
            source_turns=sources,
            eligible_fields=eligible,
            conditional_context=not handoff,
        )
    except Exception as error:
        print(f"Chat Buddy carryover error: {error}")
        return False

    for field_id, candidate in candidates.items():
        if (
            field_id in pending_fields(questionnaire)
            and candidate["source_id"] in field_sources[field_id]
            and not was_rejected(
                field_id, state["turns"][candidate["source_id"]]["message"], candidate["quote"]
            )
        ):
            st.session_state.field_suggestions[field_id] = candidate["value"]
            state["evidence"][field_id] = {**candidate, "carried": True}

    if not st.session_state.field_suggestions:
        return False

    st.session_state.review_batch_version += 1
    st.session_state.active_questionnaire = questionnaire
    description = "for D2.2" if handoff else "for the newly applicable follow-up"
    add_message("assistant", f"I found information {description} in your earlier answers. Please review it below.")
    return True


def review_activated_followups():
    state = st.session_state.carryover
    for questionnaire in QUESTIONNAIRES:
        field_sources = {}
        for child_id in bridge.get_active_conditional_fields(questionnaire):
            if child_id not in state["queued"] or child_id in bridge.answers:
                continue
            source_id, parent_value = state["queued"].pop(child_id)
            parent_id, _ = CONDITIONAL_FIELDS[child_id]
            evidence = evidence_key(state["turns"][source_id]["message"])
            attempt = (child_id, evidence)
            if bridge.answers[parent_id] == parent_value and attempt not in state["attempted"]:
                state["attempted"].add(attempt)
                field_sources[child_id] = [source_id]
        if open_carryover_review(questionnaire, field_sources):
            return True
    return False


def review_d22_handoff():
    state = st.session_state.carryover
    if state["handoff_done"]:
        return False
    state["handoff_done"] = True
    turns = [source_id for source_id, turn in state["turns"].items() if turn["questionnaire"] == "D2.1"]
    confirmed = [source_id for source_id in reversed(turns) if source_id in state["confirmed_sources"]]
    selected = list(dict.fromkeys(turns[:1] + confirmed[:3] + turns[-6:]))[:6]
    selected.sort(key=int)
    return open_carryover_review("D2.2", dict.fromkeys(pending_fields("D2.2"), selected), handoff=True)


def process_next_question():
    """
    Continue the conversation while respecting active
    conditional fields and previously confirmed answers.
    """

    if not st.session_state.intake_started:
        return

    if st.session_state.field_suggestions:
        return

    if not st.session_state.needs_next_question:
        return

    if review_activated_followups():
        return

    current_field = st.session_state.asked_field

    # Drop a previously asked conditional question if it is no longer active.
    if current_field in CONDITIONAL_FIELDS:
        active = set(bridge.get_active_conditional_fields(questionnaire_for_field(current_field)))
        if current_field not in active:
            st.session_state.asked_field = None
            st.session_state.asked_question = None
            current_field = None

    # If the current question is still required and
    # unanswered, request clarification.
    if (
        current_field is not None
        and current_field not in bridge.answers
    ):
        ask_question(
            current_field,
            clarification=True,
        )
        return

    # Otherwise, find the next active unanswered field.
    next_field = get_next_field()

    if next_field and questionnaire_for_field(next_field) == "D2.2" and review_d22_handoff():
        return

    ask_question(next_field)


# ============================================================
# ANSWER MANAGEMENT
# ============================================================

def confirm_answer(field_id, value):

    active_before = bridge.get_active_conditional_fields(questionnaire_for_field(field_id))
    valid, error = bridge.save_answer(
        field_id,
        value,
    )

    if not valid:
        return False, error

    queue_activated_followups(field_id, value, active_before)

    st.session_state.field_suggestions.pop(
        field_id,
        None,
    )

    st.session_state.editor_version += 1

    # Schedule progression after the entire
    # suggestion batch has been reviewed.
    if not st.session_state.field_suggestions:

        schedule_next_question()

    return True, None


def reject_answer(field_id):

    state = st.session_state.carryover
    evidence = state["evidence"].pop(field_id, None)
    if evidence:
        source = state["turns"][evidence["source_id"]]["message"]
        state["rejected"].setdefault(field_id, set()).add(
            (evidence_key(source), evidence_key(evidence["quote"]))
        )

    st.session_state.field_suggestions.pop(
        field_id,
        None,
    )

    if not st.session_state.field_suggestions:

        schedule_next_question()


def reset_application():

    keys = [
        "questionnaire_bridge",
        "unified_messages",
        "field_suggestions",
        "carryover",
        "asked_field",
        "asked_question",
        "retryable_turn",
        "intake_started",
        "questionnaire_complete",
        "needs_next_question",
        "clarification_needed",
        "editor_version",
        "review_batch_version",
        "active_questionnaire",
        "d23_mode",
        "d23_show_manual",
        "d23_adapter",
        "d23_active_algorithm_id",
        "d23_answer_revision",
        "d23_conversations",
        "d23-algorithm-picker",
        "d24_mode",
        "d24_adapter",
        "d24_revisions",
        "d24_conversations",
        "d24_active_scope",
        "ux_resume_algorithm",
        "ux_select_algorithm",
        "ux_resume_dataset",
        "ux_review_widget_drafts",
        "ux_d23_add",
        "ux_d23_entered",
        "ux_d23_proposal",
        "ux_d23_introductions",
        "ux_d24_add",
        "ux_d24_proposal_dataset",
        "ux_d24_proposal_function",
        "ux_d24_proposal_document",
        "ux_d24_introductions",
    ]

    for key in keys:

        st.session_state.pop(
            key,
            None,
        )

    initialize_session()


def apply_legacy_profile(candidate):
    """Replace the two legacy sections after validation and explicit confirmation."""
    st.session_state.retryable_turn = None
    st.session_state.carryover = new_carryover_state()
    st.session_state.questionnaire_bridge = candidate
    st.session_state.field_suggestions = {}
    st.session_state.asked_field = None
    st.session_state.asked_question = None
    st.session_state.intake_started = True
    st.session_state.questionnaire_complete = False
    st.session_state.d23_mode = False
    st.session_state.d24_mode = False
    st.session_state.needs_next_question = True
    st.session_state.clarification_needed = False
    st.session_state.editor_version += 1
    st.session_state.unified_messages = [
        {"role": "assistant", "content": WELCOME},
        {"role": "assistant", "content": (
            f"Restored {len(candidate.get_product_profile())} confirmed answers. "
            "I'll continue with any remaining required questions."
        )},
    ]
    st.session_state.get("ux_review_widget_drafts", {}).pop("D2.1/D2.2", None)


def apply_combined_profile(profile: CombinedProfile):
    """Replace confirmed stores only after the entire upload has validated."""
    state = st.session_state
    restored_sections = "D2.1–D2.3" if profile.dataset_evidence is None else "D2.1–D2.4"
    keep_d24_open = profile.dataset_evidence is None and state.get("d24_mode", False)
    state.update(
        questionnaire_bridge=profile.bridge,
        field_suggestions={},
        carryover=new_carryover_state(),
        asked_field=None,
        asked_question=None,
        retryable_turn=None,
        intake_started=True,
        questionnaire_complete=False,
        needs_next_question=True,
        clarification_needed=False,
        active_questionnaire="D2.1",
        editor_version=state.editor_version + 1,
        review_batch_version=state.review_batch_version + 1,
        d23_mode=keep_d24_open,
        d24_mode=keep_d24_open,
        d23_adapter=profile.algorithms,
        d23_answer_revision=state.get("d23_answer_revision", 0) + 1,
        d23_conversations={},
        unified_messages=[
            {"role": "assistant", "content": WELCOME},
            {"role": "assistant", "content": (
                f"Restored confirmed {restored_sections} answers. I'll continue with any remaining questions."
            )},
        ],
    )
    state.pop("d23_active_algorithm_id", None)
    state.pop("d23-algorithm-picker", None)
    for key in ("ux_d23_add", "ux_d23_entered", "ux_d23_proposal", "ux_d23_introductions", "ux_resume_algorithm", "ux_select_algorithm"):
        state.pop(key, None)
    saved_drafts = state.get("ux_review_widget_drafts", {})
    saved_drafts.pop("D2.1/D2.2", None)
    saved_drafts.pop("D2.3", None)
    if profile.dataset_evidence is not None:
        saved_drafts.pop("D2.4", None)
        state.update(d24_adapter=profile.dataset_evidence, d24_conversations={}, d24_revisions={})
        state.pop("d24_active_scope", None)
        for key in ("ux_d24_add", "ux_d24_proposal_dataset", "ux_d24_proposal_function",
                    "ux_d24_proposal_document", "ux_d24_introductions", "ux_resume_dataset"):
            state.pop(key, None)
        for key in list(state):
            if key.startswith("d24-"):
                state.pop(key, None)


def render_combined_restore(profile):
    st.write("Complete Chat Buddy profile" if profile.dataset_evidence is not None else "Chat Buddy profile · D2.1–D2.3")
    for questionnaire, label in (("D2.1", "Product profile"), ("D2.2", "AI function")):
        answers = profile.bridge.get_questionnaire_answers(questionnaire)
        st.caption(f"{questionnaire} — {label} · {len(answers)} confirmed answers")
        st.json(answers, expanded=False)
    st.caption(f"D2.3 — {len(profile.algorithms.algorithm_ids)} algorithm records")
    for algorithm_id in profile.algorithms.algorithm_ids:
        record = profile.algorithms.build_record(algorithm_id)
        snapshot = profile.algorithms.get_algorithm(algorithm_id)
        st.text(f"{record['record_name']} ({algorithm_id})")
        st.json(snapshot["answers"], expanded=False)
        st.caption(f"Validation findings: {len(record['validation_problems'])}. Flags: {len(record['flags'])}.")
    if profile.dataset_evidence is None:
        st.warning(
            "This version 1 backup contains D2.1–D2.3 only. Restoring it will replace those sections "
            "and preserve your current D2.4 answers."
        )
    else:
        dataset_evidence = profile.dataset_evidence
        st.caption(
            f"D2.4 — {len(dataset_evidence.record_ids('dataset'))} datasets, "
            f"{len(dataset_evidence.record_ids('function'))} evaluations, "
            f"{len(dataset_evidence.record_ids('document'))} documents"
        )
        st.caption(f"D2.4 validation findings: {len(dataset_evidence.validate())}.")
        st.warning(
            "Version 2 replaces your confirmed D2.1–D2.4 answers and clears "
            "pending suggestions, drafts, and conversation history for those sections."
        )
    st.caption("Backups preserve confirmed answers and document references. Chat quotations and history are session-only.")
    if st.button("Restore combined profile"):
        apply_combined_profile(profile)
        st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.subheader("Questionnaire Progress")
    confirmed = bridge.get_product_profile()
    overall_recorded = overall_total = 0
    for questionnaire in QUESTIONNAIRES:
        progress = bridge.get_questionnaire_progress(questionnaire)
        conditional = bridge.get_active_conditional_fields(questionnaire)
        answered = progress["completed"] + sum(field in confirmed for field in conditional)
        total = progress["total"] + len(conditional)
        overall_recorded += answered
        overall_total += total
        st.write(f"**{questionnaire} — {QUESTIONNAIRE_NAMES[questionnaire]}** · {answered}/{total} recorded")

    algorithms = st.session_state.get("d23_adapter")
    if algorithms and algorithms.algorithm_ids:
        answered, total = d23_response_progress(algorithms)
        overall_recorded += answered
        overall_total += total
        algorithm_status = f"{answered}/{total} recorded"
        if d23_section_gaps()[0]:
            algorithm_status += " · gaps to review"
    else:
        # The identity prompt is applicable before there is an algorithm record.
        overall_total += 1
        algorithm_status = "Not started"
    st.write(f"**D2.3 — Algorithm Change Control** · {algorithm_status}")

    dataset_error = None
    try:
        datasets = st.session_state.get("d24_adapter") or D24AnswerAdapter()
        backup = dump_combined_profile(bridge, algorithms, dataset_evidence=datasets)
        answered, total = d24_response_progress(datasets)
    except D24CompatibilityError as error:
        dataset_error = error
        dataset_status = "Unavailable"
    else:
        overall_recorded += answered
        overall_total += total
        dataset_status = d24_progress_status(datasets)
    st.write(f"**D2.4 — Dataset and Evidence** · {dataset_status}")
    st.write("**D2.5 — Risk Documentation** · Unavailable")
    overall = overall_recorded * 100 // overall_total if overall_total else 0
    st.progress(overall, text=f"Overall questionnaire progress · {overall}%")
    st.caption("Counts currently applicable questions. Documentation gaps are tracked separately.")

    st.subheader("Your Regulatory Profile")
    if dataset_error is not None:
        st.warning(f"Complete profile download is unavailable. {dataset_error}")
    else:
        st.download_button(
            "Download Profile", data=backup, file_name="chat_buddy_confirmed_profile_v2.json",
            mime="application/json", help="Download the combined D2.1–D2.4 confirmed profile.",
        )
    with st.expander("Other download formats"):
        st.download_button(
            "Download combined D2.1–D2.3 JSON", data=dump_combined_profile(bridge, algorithms),
            file_name="chat_buddy_confirmed_profile_v1.json", mime="application/json",
        )
        if confirmed:
            st.download_button(
                "Export Confirmed Profile", data=json.dumps(confirmed, indent=2, ensure_ascii=False),
                file_name="regulatory_d21_d22_profile.json", mime="application/json",
                help="Legacy D2.1/D2.2 only.",
            )
    uploaded = st.file_uploader("Upload Profile", type=["json"], key="profile_upload",
                                help="Accepts combined Chat Buddy backups and legacy D2.1/D2.2 JSON.")
    if uploaded is not None:
        try:
            profile = load_profile_upload(uploaded.getvalue())
        except ProfileImportError as error:
            st.error(f"Cannot restore this profile. {error}")
        else:
            if isinstance(profile, CombinedProfile):
                with st.expander("Preview uploaded Chat Buddy profile", expanded=True):
                    render_combined_restore(profile)
            else:
                st.write(f"Legacy D2.1/D2.2 profile · {len(profile.answers)} confirmed answers")
                st.warning("Restoring replaces D2.1/D2.2 answers. Existing algorithm and dataset records are preserved.")
                if st.button("Restore from JSON"):
                    apply_legacy_profile(profile)
                    st.rerun()


def render_assessment_reset():
    if st.button(
        "Start New Assessment",
        use_container_width=True,
    ):

        reset_application()

        st.rerun()


# ============================================================
# MAIN INTERFACE
# ============================================================

st.title(
    "AI Regulatory Readiness Platform"
)

st.caption(
    "Gemini-Powered Regulatory Chat Buddy"
)

st.info(
    "Preliminary regulatory readiness support only. "
    "This application does not determine regulatory "
    "approval or establish compliance."
)


chat_tab = st.container()
manual_tab = st.expander("Review & Edit", expanded=st.session_state.get("d23_show_manual", False))
with manual_tab:
    render_assessment_reset()


# ============================================================
# AUTOMATIC QUESTION PROGRESSION
# ============================================================

# Process scheduled progression before rendering
# the conversation so the next question appears
# immediately after the final confirmation.

if (
    st.session_state.needs_next_question
    and not st.session_state.field_suggestions
    and not st.session_state.get("d23_mode", False)
    and not st.session_state.get("d24_mode", False)
):

    process_next_question()


# ============================================================
# CHAT BUDDY
# ============================================================

def render_profile_transcript():
    for message in st.session_state.unified_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def render_d21_d22_chat():
    render_profile_transcript()

    # --------------------------------------------------------
    # REVIEW SUGGESTIONS
    # --------------------------------------------------------

    if st.session_state.field_suggestions:

        st.subheader(
            "Review Extracted Information"
        )

        st.info(
            "Gemini identified potential questionnaire "
            "answers. Review and confirm only information "
            "that accurately describes your product."
        )

        suggestions = (
            st.session_state.field_suggestions
        )

        for field_id, proposed in list(
            suggestions.items()
        ):

            label = bridge.get_field_label(
                field_id
            )

            field_type = bridge.get_field_type(
                field_id
            )

            display_label = (
                label
                if field_id.endswith(("-OTHER", "-DETAILS"))
                else f"{field_id} — {label}"
            )

            with st.expander(
                display_label,
                expanded=True,
            ):
                evidence = st.session_state.carryover["evidence"].get(field_id)
                if evidence and evidence.get("carried"):
                    st.caption(f'Earlier answer: “{evidence["quote"]}”')

                widget_key = (
                    f"review_{field_id}_"
                    f"{st.session_state.review_batch_version}"
                )

                if field_type == "text":

                    edited = st.text_area(
                        "Review answer",
                        value=proposed,
                        key=widget_key,
                    )

                elif field_type == "selectbox":

                    options = (
                        bridge.get_field_options(
                            field_id
                        )
                    )

                    edited = st.selectbox(
                        "Review answer",
                        options,
                        index=(
                            options.index(proposed)
                            if proposed in options
                            else 0
                        ),
                        key=widget_key,
                    )

                elif field_type == "multiselect":

                    options = (
                        bridge.get_field_options(
                            field_id
                        )
                    )

                    edited = st.multiselect(
                        "Review answer",
                        options,
                        default=proposed,
                        key=widget_key,
                    )

                else:
                    continue

                col1, col2 = st.columns(2)

                with col1:

                    if st.button(
                        "Confirm",
                        key=f"confirm_{field_id}",
                        use_container_width=True,
                    ):

                        valid, error = confirm_answer(
                            field_id,
                            edited,
                        )

                        if valid:

                            st.rerun()

                        else:

                            st.error(error)

                with col2:

                    if st.button(
                        "Reject",
                        key=f"reject_{field_id}",
                        use_container_width=True,
                    ):

                        reject_answer(
                            field_id
                        )

                        st.rerun()

    # --------------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------------

    current_field = st.session_state.asked_field
    current_question = st.session_state.asked_question
    questionnaire = st.session_state.active_questionnaire
    question_context = (questionnaire, current_field, current_question)

    retryable_turn = st.session_state.retryable_turn
    if retryable_turn and retryable_turn["context"] != question_context:
        st.session_state.retryable_turn = None
        retryable_turn = None

    retry_clicked = False
    if retryable_turn:
        st.warning(
            "Gemini couldn't process your last message. You can retry it "
            "or submit a new message."
        )
        retry_clicked = st.button(
            "Retry last message",
            disabled=bool(st.session_state.field_suggestions),
        )

    user_message = st.chat_input(
        "Describe your product or answer the question...",
        disabled=bool(st.session_state.field_suggestions),
    )

    if user_message:
        source_id = str(len(st.session_state.unified_messages))
        add_message("user", user_message)
        st.session_state.intake_started = True
    elif retry_clicked:
        user_message = retryable_turn["message"]
        source_id = retryable_turn["source_id"]

    if user_message:
        with st.spinner("Gemini is analyzing your response..."):
            try:
                confirmed_answers = bridge.get_product_profile()
                clarification = handle_user_clarification(
                    user_message=user_message,
                    current_field_id=current_field,
                    current_question=current_question,
                    confirmed_answers=confirmed_answers,
                )

                if clarification["is_clarification"]:
                    add_message("assistant", clarification["response"])
                else:
                    extracted = extract_questionnaire_fields(
                        user_message=user_message,
                        confirmed_answers=confirmed_answers,
                        target_field_id=current_field,
                        target_question=current_question,
                        questionnaire=questionnaire,
                    )
                    state = st.session_state.carryover
                    state["turns"][source_id] = {
                        "message": user_message,
                        "questionnaire": questionnaire,
                        "question": current_question,
                    }
                    extracted = {
                        field_id: value for field_id, value in extracted.items()
                        if not was_rejected(field_id, user_message)
                    }

                    if extracted:
                        st.session_state.review_batch_version += 1
                        st.session_state.field_suggestions.update(extracted)
                        state["evidence"].update({
                            field_id: {"source_id": source_id, "quote": user_message, "value": value}
                            for field_id, value in extracted.items()
                        })
                        add_message(
                            "assistant",
                            f"I identified {len(extracted)} potential questionnaire "
                            "answer(s). Please review and confirm them below.",
                        )
                    elif current_field is not None:
                        ask_question(current_field, clarification=True)
                    else:
                        add_message(
                            "assistant",
                            "I couldn't identify a supported questionnaire answer. "
                            "Could you provide more details about your product?",
                        )
                        schedule_next_question()

            except Exception as error:
                st.session_state.retryable_turn = {
                    "message": user_message,
                    "context": question_context,
                    "source_id": source_id,
                }
                print(f"Chat Buddy processing error: {error}")
            else:
                st.session_state.retryable_turn = None

        st.rerun()


def d21_d22_gaps():
    gaps = {}
    for section, validator in (("D2.1", validate_profile), ("D2.2", validate_ai_function)):
        for field_id in pending_fields(section):
            gaps[field_id] = f"{section} · {bridge.get_field_label(field_id)}"
        for issue in validator(bridge.get_questionnaire_answers(section)):
            if issue["type"] in ("missing", "conditional"):
                gaps.setdefault(issue["field_id"], f"{section} · {issue['issue']}")
    return list(gaps.values())


def resume_d21_d22():
    if st.session_state.field_suggestions:
        return False
    st.session_state.intake_started = True
    current = st.session_state.asked_field
    if current and current in pending_fields(questionnaire_for_field(current)):
        return
    next_field = get_next_field()
    if next_field:
        ask_question(next_field)
    else:
        st.info("Review the validation gaps in the Manual Questionnaire Editor.")
        return False


def navigate_to(section):
    state = st.session_state
    current = "D2.4" if state.get("d24_mode") else "D2.3" if state.get("d23_mode") else "D2.1/D2.2"
    prefix = {"D2.1/D2.2": "review_", "D2.3": "d23-review-", "D2.4": "d24-review-"}[current]
    drafts = state.setdefault("ux_review_widget_drafts", {})
    # Streamlit drops widget values when their section is hidden. Preserve inputs,
    # never the confirmation buttons that act on them.
    drafts[current] = {
        key: state[key] for key in state
        if key.startswith(prefix) and not key.endswith(("-confirm", "-reject", "-skip"))
    }
    state.update(drafts.pop(section, {}))
    state.ux_navigation_revision = state.get("ux_navigation_revision", 0) + 1
    state.pop("d23_show_manual", None)
    state.d23_mode = section in ("D2.3", "D2.4")
    state.d24_mode = section == "D2.4"
    if section == "D2.3" or current in ("D2.3", "D2.4"):
        state.ux_d23_entered = True
    if section == "D2.1/D2.2":
        # Returning to the transcript should not run carryover extraction.
        state.needs_next_question = False
    st.rerun()


with chat_tab:
    st.subheader("Product Assessment Conversation")
    if (not st.session_state.get("d23_mode") and not st.session_state.get("ux_d23_entered")
            and st.session_state.questionnaire_complete and not st.session_state.field_suggestions
            and not d21_d22_gaps()):
        navigate_to("D2.3")
    navigation_revision = st.session_state.get("ux_navigation_revision", 0)
    if st.session_state.get("d24_mode", False):
        with manual_tab:
            if st.button("Back to D2.3", key=f"section-back-d24-{navigation_revision}"):
                navigate_to("D2.3")
        render_profile_transcript()
        render_d23_history()
        render_d24_chat(tools=manual_tab)
    elif st.session_state.get("d23_mode", False):
        with manual_tab:
            if st.button("Back to D2.1 and D2.2", key=f"section-back-d23-{navigation_revision}"):
                navigate_to("D2.1/D2.2")
        render_profile_transcript()
        with st.chat_message("assistant"):
            st.write("Let’s document the algorithms that power your product’s AI functions and how changes are controlled.")
        render_d23_chat(tools=manual_tab, continue_to_datasets=lambda: navigate_to("D2.4"))
        with manual_tab:
            gaps, resume_record = d23_section_gaps()
            revision = st.session_state.d23_answer_revision
            active_id = st.session_state.get("d23_active_algorithm_id")
            if render_section_footer(
                "D2.3", gaps, next_section="D2.4",
                context=f"d23-{navigation_revision}-{active_id}-{revision}-{bool(gaps)}",
                resume=(lambda: resume_d23(resume_record)) if resume_record else None,
                show_status=bool(st.session_state.d23_adapter.algorithm_ids),
            ):
                navigate_to("D2.4")
    else:
        render_d21_d22_chat()
        if st.session_state.intake_started or st.session_state.questionnaire_complete or bridge.answers:
            gaps = d21_d22_gaps()
            with manual_tab:
                if render_section_footer(
                    "D2.1 and D2.2", gaps, next_section="D2.3",
                    context=(f"d21-d22-{navigation_revision}-{st.session_state.asked_field}-"
                             f"{st.session_state.editor_version}-{bool(gaps)}"),
                    resume=resume_d21_d22,
                ):
                    navigate_to("D2.3")


# ============================================================
# MANUAL QUESTIONNAIRE EDITOR
# ============================================================

with manual_tab:
    st.header("D2.1 and D2.2 Questionnaire Editor")

    st.caption(
        "Use this section to manually complete "
        "or correct questionnaire answers."
    )

    confirmed = bridge.get_product_profile()

    from app.chatbot.questionnaire_bridge import QUESTIONNAIRE_FIELDS
    manual_fields = []
    for questionnaire in QUESTIONNAIRES:
        for field_id in QUESTIONNAIRE_FIELDS[questionnaire]:
            manual_fields.append((field_id, bridge.get_field_label(field_id)))
        for field_id in bridge.get_active_conditional_fields(questionnaire):
            manual_fields.append((field_id, bridge.get_field_label(field_id)))

    for field_id, label in manual_fields:

        field_type = bridge.get_field_type(
            field_id
        )

        current = confirmed.get(
            field_id
        )

        with st.expander(
            f"{field_id} — {label}"
        ):

            widget_key = (
                f"manual_{field_id}_"
                f"{st.session_state.editor_version}"
            )

            if field_type == "text":

                value = st.text_area(
                    label,
                    value=current or "",
                    key=widget_key,
                )

            elif field_type == "selectbox":

                options = (
                    bridge.get_field_options(
                        field_id
                    )
                )

                value = st.selectbox(
                    label,
                    ["Select an option"] + options,
                    index=(
                        options.index(current) + 1
                        if current in options
                        else 0
                    ),
                    key=widget_key,
                )

            elif field_type == "multiselect":

                options = (
                    bridge.get_field_options(
                        field_id
                    )
                )

                value = st.multiselect(
                    label,
                    options,
                    default=current or [],
                    key=widget_key,
                )

            else:
                continue

            if st.button(
                "Save Answer",
                key=f"save_manual_{field_id}",
            ):

                if value == "Select an option":

                    st.warning(
                        "Please select an answer."
                    )

                else:

                    active_before = bridge.get_active_conditional_fields(questionnaire_for_field(field_id))
                    valid, error = bridge.save_answer(
                        field_id,
                        value,
                    )

                    if valid:

                        st.session_state.editor_version += 1
                        queue_activated_followups(field_id, value, active_before)

                        suggestions = st.session_state.field_suggestions
                        suggestions.pop(field_id, None)
                        active_conditionals = {
                            child_id
                            for questionnaire in QUESTIONNAIRES
                            for child_id in bridge.get_active_conditional_fields(questionnaire)
                        }
                        inactive_conditionals = CONDITIONAL_FIELDS.keys() - active_conditionals
                        for child_id in suggestions.keys() & inactive_conditionals:
                            suggestions.pop(child_id)
                            st.session_state.carryover["evidence"].pop(child_id, None)
                        queued = st.session_state.carryover["queued"]
                        for child_id in queued.keys() & (inactive_conditionals | {field_id}):
                            queued.pop(child_id)

                        current_field = st.session_state.asked_field
                        if (
                            not suggestions
                            and st.session_state.intake_started
                            and (
                                current_field is None
                                or current_field in bridge.answers
                                or current_field in inactive_conditionals
                            )
                        ):

                            schedule_next_question()

                        st.rerun()

                    else:

                        st.error(error)


# ============================================================
# CONFIRMED PROFILE
# ============================================================

with manual_tab:
    with st.expander("View Confirmed D2.1 and D2.2 Profile"):
        st.json(bridge.get_product_profile())
