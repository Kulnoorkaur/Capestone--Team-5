"""
AI Regulatory Readiness Platform
Context-Aware Gemini Chat Buddy Interface
"""

import streamlit as st

from app.chatbot.chat_manager import ChatManager
from app.chatbot.chat_llm import (
    evaluate_chat_answer,
    suggest_answer_from_context,
)


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


chat = st.session_state.chat_manager


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
                        f"**Based on what you've already shared, "
                        f"I suggest the following answer:**\n\n"
                        f"> {suggested_answer}\n\n"
                        f"Would you like to confirm this answer "
                        f"or change it?"
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
# PROGRESS
# ============================================================

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
                    (
                        "I'm having trouble evaluating that "
                        "answer right now. Please try again."
                    ),
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
# COMPLETED QUESTIONNAIRE
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
# RESET CONVERSATION
# ============================================================

st.divider()

if st.button("Start New Conversation"):

    chat.reset()

    st.session_state.chat_messages = []

    clear_pending_state()

    st.session_state.suggestion_checked_for = None

    present_current_question()

    st.rerun()