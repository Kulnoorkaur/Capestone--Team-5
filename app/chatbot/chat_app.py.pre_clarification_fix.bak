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
)

from app.chatbot.questionnaire_bridge import QuestionnaireBridge


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
        "asked_field": lambda: None,
        "asked_question": lambda: None,
        "intake_started": lambda: False,
        "questionnaire_complete": lambda: False,
        "needs_next_question": lambda: False,
        "clarification_needed": lambda: False,
        "editor_version": lambda: 0,
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

        if not st.session_state.questionnaire_complete:

            add_message(
                "assistant",
                "All D2.1 and D2.2 questionnaire fields are complete, "
                "including applicable conditional questions.\n\n"
                "You can review your confirmed profile "
                "or export it from the sidebar."
            )

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

    current_field = st.session_state.asked_field

    # Drop a previously asked conditional question if it is no longer active.
    from app.chatbot.questionnaire_bridge import CONDITIONAL_FIELDS
    all_conditional = set(CONDITIONAL_FIELDS)
    if current_field in all_conditional:
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

    ask_question(next_field)


# ============================================================
# ANSWER MANAGEMENT
# ============================================================

def confirm_answer(field_id, value):

    valid, error = bridge.save_answer(
        field_id,
        value,
    )

    if not valid:
        return False, error

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
        "asked_field",
        "asked_question",
        "intake_started",
        "questionnaire_complete",
        "needs_next_question",
        "clarification_needed",
        "editor_version",
        "active_questionnaire",
    ]

    for key in keys:

        st.session_state.pop(
            key,
            None,
        )

    initialize_session()


def restore_profile(uploaded_file):
    """Validate first; replace session only when all answers are valid."""
    try:
        raw = uploaded_file.getvalue()
        if len(raw) > 1_000_000:
            return False, "File exceeds 1 MB."
        profile = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return False, f"Invalid JSON: {error}"
    if not isinstance(profile, dict):
        return False, "Expected a JSON object mapping field IDs to answers."
    candidate = QuestionnaireBridge()
    from app.chatbot.questionnaire_bridge import QUESTIONNAIRE_FIELDS, CONDITIONAL_FIELDS
    primary = {field_id for fields in QUESTIONNAIRE_FIELDS.values() for field_id in fields}
    conditional = set(CONDITIONAL_FIELDS)
    unknown = set(profile) - primary - conditional
    if unknown:
        return False, "Unknown fields: " + ", ".join(sorted(unknown))
    # Restore parents before children, irrespective of JSON key order.
    for field_id in sorted(primary):
        if field_id in profile:
            valid, error = candidate.save_answer(field_id, profile[field_id])
            if not valid:
                return False, f"{field_id}: {error}"
    active = set()
    for questionnaire in QUESTIONNAIRES:
        active.update(candidate.get_active_conditional_fields(questionnaire))
    inactive = (set(profile) & conditional) - active
    if inactive:
        return False, "Inactive conditional fields in backup: " + ", ".join(sorted(inactive))
    for field_id in sorted(active):
        if field_id in profile:
            valid, error = candidate.save_answer(field_id, profile[field_id])
            if not valid:
                return False, f"{field_id}: {error}"
    st.session_state.questionnaire_bridge = candidate
    st.session_state.field_suggestions = {}
    st.session_state.asked_field = None
    st.session_state.asked_question = None
    st.session_state.intake_started = True
    st.session_state.questionnaire_complete = False
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
    return True, None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("Regulatory Profile")

    confirmed = bridge.get_product_profile()

    st.subheader("Questionnaire Progress")
    overall_completed = overall_total = 0
    for questionnaire in QUESTIONNAIRES:
        progress = bridge.get_questionnaire_progress(questionnaire)
        overall_completed += progress["completed"]
        overall_total += progress["total"]
        st.write(f"**{questionnaire} — {QUESTIONNAIRE_NAMES[questionnaire]}:** "
                 f"{progress['completed']}/{progress['total']}")
        conditional_fields = bridge.get_active_conditional_fields(questionnaire)
        if conditional_fields:
            conditional_completed = sum(fid in confirmed for fid in conditional_fields)
            st.caption(f"Conditional: {conditional_completed}/{len(conditional_fields)}")
    st.progress(overall_completed / overall_total if overall_total else 0)
    st.caption(f"Overall primary questions: {overall_completed}/{overall_total}")

    st.divider()

    st.subheader("Additional Questionnaires")

    st.write(
        "D2.3 — Algorithm Change Control: Not connected"
    )

    st.write(
        "D2.4 — Dataset and Evidence: Not connected"
    )

    st.write(
        "D2.5 — Risk Documentation: Not connected"
    )

    st.divider()

    if confirmed:

        st.download_button(
            "Export Confirmed Profile",
            data=json.dumps(
                confirmed,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="regulatory_d21_d22_profile.json",
            mime="application/json",
            use_container_width=True,
        )

    st.subheader("Restore Saved Profile")
    uploaded_profile = st.file_uploader(
        "Choose a previously exported JSON profile",
        type=["json"],
        key="restore_profile_upload",
    )
    if st.button("Restore from JSON", disabled=uploaded_profile is None,
                 use_container_width=True):
        success, error = restore_profile(uploaded_profile)
        if success:
            st.rerun()
        else:
            st.error(error)

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


chat_tab, manual_tab = st.tabs(
    [
        "Chat Buddy",
        "Manual Questionnaire Editor",
    ]
)


# ============================================================
# AUTOMATIC QUESTION PROGRESSION
# ============================================================

# Process scheduled progression before rendering
# the conversation so the next question appears
# immediately after the final confirmation.

if (
    st.session_state.needs_next_question
    and not st.session_state.field_suggestions
):

    process_next_question()


# ============================================================
# CHAT BUDDY
# ============================================================

with chat_tab:

    st.subheader(
        "Product Assessment Conversation"
    )

    # --------------------------------------------------------
    # DISPLAY CONVERSATION
    # --------------------------------------------------------

    for message in st.session_state.unified_messages:

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

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

            with st.expander(
                f"{field_id} — {label}",
                expanded=True,
            ):

                widget_key = (
                    f"review_{field_id}_"
                    f"{st.session_state.editor_version}"
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

    user_message = st.chat_input(
        "Describe your product or answer the question...",
        disabled=bool(
            st.session_state.field_suggestions
        ),
    )

    if user_message:

        add_message(
            "user",
            user_message,
        )

        st.session_state.intake_started = True

        with st.spinner(
            "Gemini is analyzing your response..."
        ):

            try:

                extracted = extract_questionnaire_fields(
                    user_message=user_message,
                    confirmed_answers=bridge.get_product_profile(),
                    target_field_id=st.session_state.asked_field,
                    target_question=st.session_state.asked_question,
                    questionnaire=st.session_state.active_questionnaire,
                )

                if extracted:

                    st.session_state.field_suggestions.update(
                        extracted
                    )

                    add_message(
                        "assistant",
                        (
                            f"I identified {len(extracted)} "
                            "potential questionnaire answer(s). "
                            "Please review and confirm them below."
                        ),
                    )

                elif st.session_state.asked_field is not None:

                    # Gemini did not capture the current field.
                    # Ask for clarification without losing focus.

                    ask_question(
                        st.session_state.asked_field,
                        clarification=True,
                    )

                else:

                    add_message(
                        "assistant",
                        (
                            "I couldn't identify a supported "
                            "questionnaire answer. Could you "
                            "provide more details about your product?"
                        ),
                    )

            except Exception as error:

                add_message(
                    "assistant",
                    (
                        "I couldn't process that response. "
                        "Please try again."
                    ),
                )

                st.error(str(error))

        # After the initial product description,
        # Gemini extracts suggestions first.
        # If nothing was extracted and no question
        # is active, schedule the next question.

        if (
            not st.session_state.field_suggestions
            and st.session_state.asked_field is None
        ):

            schedule_next_question()

        st.rerun()


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

                    valid, error = bridge.save_answer(
                        field_id,
                        value,
                    )

                    if valid:

                        st.session_state.editor_version += 1

                        st.session_state.field_suggestions.pop(
                            field_id,
                            None,
                        )

                        # Continue the conversation when
                        # all suggestions are resolved.

                        if (
                            not st.session_state.field_suggestions
                            and st.session_state.intake_started
                        ):

                            schedule_next_question()

                        st.rerun()

                    else:

                        st.error(error)


# ============================================================
# CONFIRMED PROFILE
# ============================================================

st.divider()

with st.expander(
    "View Confirmed D2.1 and D2.2 Profile"
):

    st.json(
        bridge.get_product_profile()
    )
