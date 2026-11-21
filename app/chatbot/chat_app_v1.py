"""
AI Regulatory Readiness Platform
Unified Gemini Chat Buddy — D2.1

Conversational questionnaire with:
- Gemini field extraction
- User confirmation
- Missing-field questions
- Optional manual editing
- Structured profile export
"""

import json

import streamlit as st

from app.chatbot.chat_llm import extract_questionnaire_fields
from app.chatbot.questionnaire_bridge import QuestionnaireBridge


st.set_page_config(
    page_title="AI Regulatory Readiness Platform",
    page_icon="💬",
    layout="wide",
)


# ============================================================
# SESSION STATE
# ============================================================

if "questionnaire_bridge" not in st.session_state:
    st.session_state.questionnaire_bridge = QuestionnaireBridge()

if "unified_messages" not in st.session_state:
    st.session_state.unified_messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome! I'll help you build a regulatory readiness "
                "profile for your imaging AI product.\n\n"
                "To begin, describe your product, what it does, "
                "and who will use it."
            ),
        }
    ]

if "field_suggestions" not in st.session_state:
    st.session_state.field_suggestions = {}

if "asked_field" not in st.session_state:
    st.session_state.asked_field = None

bridge = st.session_state.questionnaire_bridge


# ============================================================
# HELPERS
# ============================================================

def add_message(role, content):
    st.session_state.unified_messages.append(
        {"role": role, "content": content}
    )


def get_next_field():
    """Return the next unanswered active field."""

    for field_id in bridge.get_missing_fields():
        return field_id

    for field_id in bridge.get_active_conditional_fields():
        if field_id not in bridge.answers:
            return field_id

    return None


def ask_next_question():
    """Ask about the next missing questionnaire field."""

    field_id = get_next_field()

    st.session_state.asked_field = field_id

    if field_id is None:
        add_message(
            "assistant",
            "All D2.1 fields have been completed. "
            "You can review your profile or export it.",
        )
        return

    label = bridge.get_field_label(field_id)
    field_type = bridge.get_field_type(field_id)

    options = bridge.get_field_options(field_id)

    question = f"Next, could you provide: **{label}**?"

    if field_type in ("selectbox", "multiselect"):
        question += "\n\nAvailable options: " + ", ".join(options)

    add_message("assistant", question)


def extract_suggestions(message):
    """Extract new questionnaire suggestions using Gemini."""

    return extract_questionnaire_fields(
        user_message=message,
        confirmed_answers=bridge.get_product_profile(),
    )


def reset_application():
    st.session_state.questionnaire_bridge = QuestionnaireBridge()
    st.session_state.field_suggestions = {}
    st.session_state.asked_field = None
    st.session_state.unified_messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome! Describe your imaging AI product, "
                "what it does, and who will use it."
            ),
        }
    ]


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("Regulatory Profile")

    confirmed = bridge.get_product_profile()

    completed = sum(
        1 for field_id in bridge.field_labels
        if field_id in confirmed
    )

    st.subheader("Questionnaire Progress")

    st.progress(completed / 24)

    st.write(f"**D2.1 Product Profile:** {completed}/24")

    st.caption("Additional questionnaires will be integrated next.")

    st.divider()

    st.write("D2.2 — AI Function: Not connected")
    st.write("D2.3 — Algorithm Change Control: Not connected")
    st.write("D2.4 — Dataset and Evidence: Not connected")
    st.write("D2.5 — Risk Documentation: Not connected")

    st.divider()

    if confirmed:
        st.download_button(
            "Export Confirmed Profile",
            data=json.dumps(confirmed, indent=2),
            file_name="regulatory_product_profile.json",
            mime="application/json",
            use_container_width=True,
        )

    if st.button("Start New Assessment", use_container_width=True):
        reset_application()
        st.rerun()


# ============================================================
# MAIN INTERFACE
# ============================================================

st.title("AI Regulatory Readiness Platform")

st.caption("Gemini-Powered Regulatory Chat Buddy")

st.info(
    "Preliminary regulatory readiness support only. "
    "This application does not determine regulatory approval "
    "or establish compliance."
)

chat_tab, manual_tab = st.tabs(
    ["Chat Buddy", "Manual Questionnaire Editor"]
)


# ============================================================
# CHAT BUDDY
# ============================================================

with chat_tab:

    st.subheader("Product Assessment Conversation")

    for message in st.session_state.unified_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --------------------------------------------------------
    # REVIEW SUGGESTIONS
    # --------------------------------------------------------

    suggestions = st.session_state.field_suggestions

    if suggestions:

        st.subheader("Review Extracted Information")

        st.info(
            "Gemini identified potential questionnaire answers. "
            "Confirm only information that accurately describes "
            "your product."
        )

        for field_id, value in list(suggestions.items()):

            field_type = bridge.get_field_type(field_id)
            label = bridge.get_field_label(field_id)

            with st.expander(
                f"{field_id} — {label}",
                expanded=True,
            ):

                if field_type == "text":
                    edited = st.text_area(
                        "Review answer",
                        value=value,
                        key=f"edit_{field_id}",
                    )

                elif field_type == "selectbox":
                    options = bridge.get_field_options(field_id)
                    edited = st.selectbox(
                        "Review answer",
                        options,
                        index=options.index(value),
                        key=f"edit_{field_id}",
                    )

                elif field_type == "multiselect":
                    options = bridge.get_field_options(field_id)
                    edited = st.multiselect(
                        "Review answer",
                        options,
                        default=value,
                        key=f"edit_{field_id}",
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
                        valid, error = bridge.save_answer(
                            field_id, edited
                        )

                        if valid:
                            del st.session_state.field_suggestions[field_id]
                            st.rerun()
                        else:
                            st.error(error)

                with col2:
                    if st.button(
                        "Reject",
                        key=f"reject_{field_id}",
                        use_container_width=True,
                    ):
                        del st.session_state.field_suggestions[field_id]
                        st.rerun()

    # --------------------------------------------------------
    # CHAT INPUT
    # --------------------------------------------------------

    user_message = st.chat_input(
        "Describe your product or answer the question..."
    )

    if user_message:

        add_message("user", user_message)

        with st.spinner("Gemini is analyzing your response..."):
            try:
                extracted = extract_suggestions(user_message)
                st.session_state.field_suggestions.update(extracted)

                if extracted:
                    add_message(
                        "assistant",
                        (
                            f"I identified {len(extracted)} potential "
                            "questionnaire answers. Please review "
                            "and confirm them below."
                        ),
                    )
                else:
                    add_message(
                        "assistant",
                        (
                            "I couldn't identify a new structured "
                            "answer from that response. Could you "
                            "provide more detail?"
                        ),
                    )

            except Exception as error:
                st.error("Gemini could not process your response.")
                st.exception(error)

        st.rerun()

    # --------------------------------------------------------
    # NEXT QUESTION
    # --------------------------------------------------------

    if (
        not st.session_state.field_suggestions
        and st.session_state.unified_messages[-1]["role"] == "assistant"
        and len(st.session_state.unified_messages) > 1
    ):

        if st.session_state.asked_field is None:
            ask_next_question()
            st.rerun()


# ============================================================
# MANUAL QUESTIONNAIRE EDITOR
# ============================================================

with manual_tab:

    st.header("D2.1 Product and Intended-Use Profile")

    st.caption(
        "Use this section to manually complete or correct "
        "questionnaire answers."
    )

    confirmed = bridge.get_product_profile()

    for field_id, label in bridge.field_labels.items():

        field_type = bridge.get_field_type(field_id)
        current = confirmed.get(field_id)

        with st.expander(f"{field_id} — {label}"):

            if field_type == "text":
                value = st.text_area(
                    label,
                    value=current or "",
                    key=f"manual_{field_id}",
                )

            elif field_type == "selectbox":
                options = bridge.get_field_options(field_id)
                value = st.selectbox(
                    label,
                    ["Select an option"] + options,
                    index=(
                        options.index(current) + 1
                        if current in options
                        else 0
                    ),
                    key=f"manual_{field_id}",
                )

            elif field_type == "multiselect":
                options = bridge.get_field_options(field_id)
                value = st.multiselect(
                    label,
                    options,
                    default=current or [],
                    key=f"manual_{field_id}",
                )

            else:
                continue

            if st.button(
                "Save Answer",
                key=f"save_manual_{field_id}",
            ):

                if value == "Select an option":
                    st.warning("Please select an answer.")
                else:
                    valid, error = bridge.save_answer(
                        field_id, value
                    )

                    if valid:
                        st.success("Answer saved.")
                        st.rerun()
                    else:
                        st.error(error)


# ============================================================
# CONFIRMED PROFILE
# ============================================================

st.divider()

with st.expander("View Confirmed D2.1 Profile"):

    st.json(bridge.get_product_profile())