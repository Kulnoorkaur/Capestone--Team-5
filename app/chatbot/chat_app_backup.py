"""
AI Regulatory Readiness Platform
Context-Aware Gemini Chat Buddy Interface

Features:
1. Conversational product questionnaire.
2. Gemini-powered answer evaluation.
3. Clarification questions.
4. Context-aware answer suggestions.
5. D2.1 questionnaire field extraction.
6. Field validation and user confirmation.
7. Structured product profile export.
"""

import json

import streamlit as st

from app.chatbot.chat_manager import ChatManager
from app.chatbot.chat_llm import (
    evaluate_chat_answer,
    suggest_answer_from_context,
    extract_questionnaire_fields,
)
from app.chatbot.questionnaire_bridge import QuestionnaireBridge


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Regulatory Chat Buddy",
    page_icon="💬",
    layout="centered",
)

st.title("AI Regulatory Chat Buddy")

st.caption(
    "Your conversational guide to AI medical device regulatory readiness."
)

st.info(
    "This assistant provides preliminary guidance only. "
    "It does not establish regulatory compliance or approval."
)


# ============================================================
# SESSION INITIALIZATION
# ============================================================

if "chat_manager" not in st.session_state:
    st.session_state.chat_manager = ChatManager()

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "pending_clarification" not in st.session_state:
    st.session_state.pending_clarification = None

if "pending_answer" not in st.session_state:
    st.session_state.pending_answer = None

if "awaiting_confirmation" not in st.session_state:
    st.session_state.awaiting_confirmation = False

if "editing_suggestion" not in st.session_state:
    st.session_state.editing_suggestion = False

if "suggestion_checked_for" not in st.session_state:
    st.session_state.suggestion_checked_for = None

# D2.1 integration state

if "questionnaire_bridge" not in st.session_state:
    st.session_state.questionnaire_bridge = QuestionnaireBridge()

if "d21_suggestions" not in st.session_state:
    st.session_state.d21_suggestions = {}

chat = st.session_state.chat_manager
bridge = st.session_state.questionnaire_bridge


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def add_message(role, content):
    """Add a message to the conversation history."""

    st.session_state.chat_messages.append(
        {
            "role": role,
            "content": content,
        }
    )


def clear_pending_state():
    """Clear temporary clarification and suggestion state."""

    st.session_state.pending_clarification = None
    st.session_state.pending_answer = None
    st.session_state.awaiting_confirmation = False
    st.session_state.editing_suggestion = False


def present_current_question():
    """
    Present the next questionnaire question.

    If previous answers support a suggestion, ask the
    user to confirm it rather than repeating the question.
    """

    if chat.is_complete():
        add_message(
            "assistant",
            "You've completed the initial product questionnaire! "
            "Your confirmed responses are available below.",
        )
        return

    current_question = chat.get_current_question()
    question_id = current_question["id"]

    # Avoid repeating the same suggestion check.
    if st.session_state.suggestion_checked_for == question_id:
        add_message(
            "assistant",
            current_question["question"],
        )
        return

    st.session_state.suggestion_checked_for = question_id

    previous_answers = chat.get_previous_answers()

    if previous_answers:

        try:
            suggestion_result = suggest_answer_from_context(
                question=current_question["question"],
                previous_answers=previous_answers,
            )

            if suggestion_result["can_suggest"]:

                suggested_answer = suggestion_result[
                    "suggested_answer"
                ]

                chat.suggest_answer(
                    question_id,
                    suggested_answer,
                )

                st.session_state.awaiting_confirmation = True

                add_message(
                    "assistant",
                    (
                        "**Based on what you've already shared, "
                        "I suggest the following answer:**\n\n"
                        f"> {suggested_answer}\n\n"
                        "Would you like to confirm this answer "
                        "or change it?"
                    ),
                )

                return

        except Exception:
            # A failed suggestion request should not prevent
            # the user from answering the questionnaire.
            pass

    add_message(
        "assistant",
        current_question["question"],
    )


# ============================================================
# START CONVERSATION
# ============================================================

if not st.session_state.chat_messages:
    present_current_question()


# ============================================================
# INITIAL QUESTIONNAIRE PROGRESS
# ============================================================

st.subheader("Initial Product Questionnaire")

st.progress(chat.get_progress() / 100)

st.caption(
    f"Questionnaire progress: {chat.get_progress()}%"
)


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state.chat_messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ============================================================
# SUGGESTION CONFIRMATION
# ============================================================

if (
    not chat.is_complete()
    and st.session_state.awaiting_confirmation
):

    current_question = chat.get_current_question()

    suggestion = chat.get_suggestion(
        current_question["id"]
    )

    if suggestion:

        st.write("**Review the suggested answer:**")

        st.info(suggestion)

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Confirm this answer",
                use_container_width=True,
            ):

                confirmed = chat.confirm_suggestion()

                if confirmed:

                    add_message(
                        "user",
                        "I confirm this answer.",
                    )

                    add_message(
                        "assistant",
                        "Thank you. I've recorded your "
                        "confirmed answer.",
                    )

                    clear_pending_state()

                    present_current_question()

                    st.rerun()

        with col2:

            if st.button(
                "I'd like to change it",
                use_container_width=True,
            ):

                chat.reject_suggestion()

                st.session_state.awaiting_confirmation = False
                st.session_state.editing_suggestion = True

                add_message(
                    "user",
                    "I'd like to change that answer.",
                )

                add_message(
                    "assistant",
                    (
                        "No problem. Please provide your "
                        "preferred answer to this question:\n\n"
                        + current_question["question"]
                    ),
                )

                st.rerun()


# ============================================================
# HANDLE USER ANSWERS
# ============================================================

if (
    not chat.is_complete()
    and not st.session_state.awaiting_confirmation
):

    user_answer = st.chat_input(
        "Type your answer here..."
    )

    if user_answer:

        current_question = chat.get_current_question()

        add_message(
            "user",
            user_answer,
        )

        # Combine an original answer with any clarification.
        if st.session_state.pending_clarification:

            combined_answer = (
                st.session_state.pending_answer
                + "\nAdditional clarification: "
                + user_answer
            )

        else:
            combined_answer = user_answer

        with st.spinner("Thinking..."):

            try:

                result = evaluate_chat_answer(
                    question=current_question["question"],
                    answer=combined_answer,
                    previous_answers=chat.get_previous_answers(),
                )

            except Exception as error:

                add_message(
                    "assistant",
                    "I'm having trouble evaluating that "
                    "answer right now. Please try again.",
                )

                st.error(
                    "Gemini is temporarily unavailable."
                )

                st.exception(error)

                st.stop()

        assistant_message = result["message"]

        if result["needs_clarification"]:

            st.session_state.pending_clarification = (
                result["clarification_question"]
            )

            st.session_state.pending_answer = combined_answer

            add_message(
                "assistant",
                (
                    assistant_message
                    + "\n\n**Follow-up question:** "
                    + result["clarification_question"]
                ),
            )

        else:

            saved = chat.save_answer(combined_answer)

            if saved:

                clear_pending_state()

                add_message(
                    "assistant",
                    assistant_message,
                )

                present_current_question()

        st.rerun()


# ============================================================
# COMPLETED INITIAL QUESTIONNAIRE
# ============================================================

if chat.is_complete():

    st.success(
        "Initial product questionnaire completed!"
    )

    with st.expander(
        "View Your Confirmed Product Profile",
        expanded=True,
    ):

        st.json(
            chat.get_product_profile()
        )


# ============================================================
# D2.1 GEMINI QUESTIONNAIRE INTEGRATION
# ============================================================

st.divider()

st.header("D2.1 — AI-Assisted Product Profile")

st.caption(
    "Describe your imaging AI product. Gemini will identify "
    "relevant questionnaire fields for your review."
)

product_description = st.text_area(
    "Describe your AI medical device",
    placeholder=(
        "Example: LungScan AI analyzes chest CT scans "
        "and highlights suspicious lung nodules for radiologists."
    ),
    key="d21_product_description",
)

if st.button(
    "Extract D2.1 Fields",
    use_container_width=True,
):

    if not product_description.strip():

        st.warning(
            "Please enter a product description."
        )

    else:

        with st.spinner(
            "Gemini is analyzing your product description..."
        ):

            try:

                suggestions = extract_questionnaire_fields(
                    user_message=product_description,
                    confirmed_answers=bridge.get_product_profile(),
                )

                st.session_state.d21_suggestions = suggestions

                # Clear old review widget values.
                for key in list(st.session_state.keys()):

                    if key.startswith("review_"):
                        del st.session_state[key]

                if suggestions:

                    st.success(
                        f"Gemini identified {len(suggestions)} "
                        "potential questionnaire answers."
                    )

                else:

                    st.info(
                        "No new questionnaire fields were identified."
                    )

            except Exception as error:

                st.error(
                    "Unable to extract questionnaire fields."
                )

                st.exception(error)


# ============================================================
# REVIEW GEMINI SUGGESTIONS
# ============================================================

suggestions = st.session_state.d21_suggestions

if suggestions:

    st.divider()

    st.subheader("Review Suggested Answers")

    st.info(
        "These answers were generated by Gemini. "
        "Review each answer before confirming it. "
        "You may edit or reject any suggestion."
    )

    for field_id, suggested_value in list(suggestions.items()):

        field_label = bridge.get_field_label(field_id)
        field_type = bridge.get_field_type(field_id)

        with st.expander(
            f"{field_id} — {field_label}",
            expanded=True,
        ):

            st.write("**Gemini suggested:**")

            st.write(suggested_value)

            # --------------------------------------------
            # TEXT FIELDS
            # --------------------------------------------

            if field_type == "text":

                edited_value = st.text_area(
                    "Review or edit this answer",
                    value=suggested_value,
                    key=f"review_{field_id}",
                )

            # --------------------------------------------
            # SELECTBOX FIELDS
            # --------------------------------------------

            elif field_type == "selectbox":

                options = bridge.get_field_options(field_id)

                edited_value = st.selectbox(
                    "Select the correct answer",
                    options,
                    index=options.index(suggested_value),
                    key=f"review_{field_id}",
                )

            # --------------------------------------------
            # MULTISELECT FIELDS
            # --------------------------------------------

            elif field_type == "multiselect":

                options = bridge.get_field_options(field_id)

                edited_value = st.multiselect(
                    "Select the correct answers",
                    options,
                    default=suggested_value,
                    key=f"review_{field_id}",
                )

            else:

                st.warning(
                    "Unsupported questionnaire field."
                )

                continue

            # --------------------------------------------
            # CONFIRM OR REJECT
            # --------------------------------------------

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "Confirm Answer",
                    key=f"confirm_{field_id}",
                    use_container_width=True,
                ):

                    valid, error = bridge.save_answer(
                        field_id,
                        edited_value,
                    )

                    if valid:

                        del st.session_state.d21_suggestions[
                            field_id
                        ]

                        st.rerun()

                    else:

                        st.error(error)

            with col2:

                if st.button(
                    "Reject Suggestion",
                    key=f"reject_{field_id}",
                    use_container_width=True,
                ):

                    del st.session_state.d21_suggestions[
                        field_id
                    ]

                    st.rerun()


# ============================================================
# CONFIRMED D2.1 PROFILE
# ============================================================

st.divider()

st.subheader("Confirmed D2.1 Product Profile")

confirmed_profile = bridge.get_product_profile()

confirmed_primary_fields = sum(
    1
    for field_id in bridge.field_labels
    if field_id in confirmed_profile
)

st.progress(
    confirmed_primary_fields / 24
)

st.metric(
    "Confirmed Primary Fields",
    f"{confirmed_primary_fields} / 24",
)

st.caption(
    f"{len(bridge.get_missing_fields())} of 24 "
    "primary D2.1 fields remain unanswered."
)

# Display active conditional fields.
active_conditional_fields = (
    bridge.get_active_conditional_fields()
)

if active_conditional_fields:

    st.subheader("Additional Information Required")

    for field_id in active_conditional_fields:

        if field_id in confirmed_profile:
            continue

        field_label = field_id.replace("-", " ").title()

        conditional_answer = st.text_area(
            f"{field_label}",
            key=f"conditional_{field_id}",
        )

        if st.button(
            f"Save {field_id}",
            key=f"save_conditional_{field_id}",
        ):

            valid, error = bridge.save_answer(
                field_id,
                conditional_answer,
            )

            if valid:
                st.success(
                    "Additional information saved."
                )
                st.rerun()

            else:
                st.error(error)


# ============================================================
# DISPLAY AND EXPORT CONFIRMED ANSWERS
# ============================================================

if confirmed_profile:

    with st.expander(
        "View Confirmed D2.1 Answers",
        expanded=True,
    ):

        st.json(confirmed_profile)

    st.download_button(
        "Download Confirmed D2.1 Profile",
        data=json.dumps(
            confirmed_profile,
            indent=2,
            ensure_ascii=False,
        ),
        file_name="d21_product_profile.json",
        mime="application/json",
        use_container_width=True,
    )

else:

    st.info(
        "No D2.1 fields have been confirmed yet."
    )


# ============================================================
# RESET CONVERSATION
# ============================================================

st.divider()

if st.button(
    "Start New Conversation",
    use_container_width=True,
):

    # Reset original Chat Buddy.
    chat.reset()

    st.session_state.chat_messages = []

    clear_pending_state()

    st.session_state.suggestion_checked_for = None

    # Reset D2.1 questionnaire integration.
    st.session_state.questionnaire_bridge = QuestionnaireBridge()

    st.session_state.d21_suggestions = {}

    st.session_state.pop(
        "d21_product_description",
        None,
    )

    # Clear review and conditional widget values.
    for key in list(st.session_state.keys()):

        if (
            key.startswith("review_")
            or key.startswith("conditional_")
        ):
            del st.session_state[key]

    present_current_question()

    st.rerun()