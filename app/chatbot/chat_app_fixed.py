"""Streamlit D2.1 conversational intake for AI Regulatory Readiness Platform."""
import json
import streamlit as st

from app.chatbot.chat_llm import (
    extract_questionnaire_fields,
    generate_questionnaire_question,
)
from app.chatbot.questionnaire_bridge import QuestionnaireBridge

st.set_page_config(page_title="AI Regulatory Readiness Platform", page_icon="💬", layout="wide")

WELCOME = (
    "Welcome! I'll help you build a regulatory readiness profile for your "
    "imaging AI product.\n\nDescribe your product, what it does, and who will use it."
)


def init_state():
    defaults = {
        "questionnaire_bridge": QuestionnaireBridge,
        "unified_messages": lambda: [{"role": "assistant", "content": WELCOME}],
        "field_suggestions": dict,
        "asked_field": lambda: None,
        "asked_question": lambda: None,
        "intake_started": lambda: False,
        "questionnaire_complete": lambda: False,
        "editor_version": lambda: 0,
        "clarification_count": lambda: 0,
    }
    for name, factory in defaults.items():
        if name not in st.session_state:
            st.session_state[name] = factory()


init_state()
bridge = st.session_state.questionnaire_bridge


def say(role, message):
    st.session_state.unified_messages.append({"role": role, "content": message})


def next_field():
    for field_id in bridge.get_active_conditional_fields():
        if field_id not in bridge.answers:
            return field_id
    for field_id in bridge.get_missing_fields():
        if field_id not in bridge.answers:
            return field_id
    return None


def fallback_question(field_id):
    label = bridge.get_field_label(field_id)
    options = bridge.get_field_options(field_id)
    result = f"Could you describe the **{label.lower()}** for your product?"
    if options:
        result += "\n\nChoose from: " + ", ".join(options)
    return result


def ask_field(field_id, clarification=False):
    """Ask one question and keep the target field available for extraction."""
    if field_id is None:
        st.session_state.asked_field = None
        st.session_state.asked_question = None
        if not st.session_state.questionnaire_complete:
            say("assistant", "All D2.1 primary and active conditional fields are complete. "
                "Review your confirmed profile or export it from the sidebar.")
            st.session_state.questionnaire_complete = True
        return

    try:
        question = generate_questionnaire_question(
            field_id=field_id,
            field_label=bridge.get_field_label(field_id),
            field_type=bridge.get_field_type(field_id),
            field_options=bridge.get_field_options(field_id),
            confirmed_answers=bridge.get_product_profile(),
        )
    except Exception:
        question = fallback_question(field_id)

    if clarification:
        question = (
            f"I still need to confirm **{bridge.get_field_label(field_id)}**. "
            f"{question}\n\nYou can also enter this answer in the Manual Questionnaire Editor."
        )
    st.session_state.asked_field = field_id
    st.session_state.asked_question = question
    st.session_state.questionnaire_complete = False
    say("assistant", question)


def continue_after_review():
    """Called only when the entire pending suggestion batch is resolved."""
    if st.session_state.field_suggestions or not st.session_state.intake_started:
        return
    target = st.session_state.asked_field
    if target is not None and target not in bridge.answers:
        st.session_state.clarification_count += 1
        ask_field(target, clarification=True)
    else:
        st.session_state.clarification_count = 0
        ask_field(next_field())


def reset():
    for name in (
        "questionnaire_bridge", "unified_messages", "field_suggestions",
        "asked_field", "asked_question", "intake_started",
        "questionnaire_complete", "editor_version", "clarification_count",
    ):
        st.session_state.pop(name, None)
    init_state()


def save_confirmed(field_id, value):
    valid, error = bridge.save_answer(field_id, value)
    if valid:
        st.session_state.field_suggestions.pop(field_id, None)
        st.session_state.editor_version += 1
    return valid, error


def review_widget(field_id, proposed):
    field_type = bridge.get_field_type(field_id)
    key = f"review_{field_id}_{st.session_state.editor_version}"
    if field_type == "text":
        return st.text_area("Review answer", value=proposed, key=key)
    options = bridge.get_field_options(field_id)
    if field_type == "selectbox":
        return st.selectbox("Review answer", options,
                            index=options.index(proposed) if proposed in options else 0,
                            key=key)
    if field_type == "multiselect":
        return st.multiselect("Review answer", options,
                              default=[x for x in proposed if x in options], key=key)
    return None


with st.sidebar:
    st.title("Regulatory Profile")
    confirmed = bridge.get_product_profile()
    completed = sum(field_id in confirmed for field_id in bridge.field_labels)
    total = len(bridge.field_labels)
    st.subheader("Questionnaire Progress")
    st.progress(completed / total if total else 0)
    st.write(f"**D2.1 Product Profile:** {completed}/{total}")
    active = bridge.get_active_conditional_fields()
    if active:
        st.caption(f"Conditional fields: {sum(x in confirmed for x in active)}/{len(active)}")
    st.divider()
    st.write("D2.2 — AI Function: Not connected")
    st.write("D2.3 — Algorithm Change Control: Not connected")
    st.write("D2.4 — Dataset and Evidence: Not connected")
    st.write("D2.5 — Risk Documentation: Not connected")
    st.divider()
    if confirmed:
        st.download_button("Export Confirmed Profile", json.dumps(confirmed, indent=2),
                           file_name="regulatory_product_profile.json",
                           mime="application/json", use_container_width=True)
    if st.button("Start New Assessment", use_container_width=True):
        reset()
        st.rerun()

st.title("AI Regulatory Readiness Platform")
st.caption("Gemini-Powered Regulatory Chat Buddy")
st.info("Preliminary regulatory readiness support only. This application does not "
        "determine regulatory approval or establish compliance.")
chat_tab, manual_tab = st.tabs(["Chat Buddy", "Manual Questionnaire Editor"])

with chat_tab:
    st.subheader("Product Assessment Conversation")
    for message in st.session_state.unified_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if st.session_state.field_suggestions:
        st.subheader("Review Extracted Information")
        st.info("Review each proposed answer. Nothing is saved until you confirm it.")
        for field_id, proposed in list(st.session_state.field_suggestions.items()):
            with st.expander(f"{field_id} — {bridge.get_field_label(field_id)}", expanded=True):
                edited = review_widget(field_id, proposed)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirm", key=f"confirm_{field_id}", use_container_width=True):
                        valid, error = save_confirmed(field_id, edited)
                        if valid:
                            if not st.session_state.field_suggestions:
                                continue_after_review()
                            st.rerun()
                        else:
                            st.error(error)
                with col2:
                    if st.button("Reject", key=f"reject_{field_id}", use_container_width=True):
                        st.session_state.field_suggestions.pop(field_id, None)
                        if not st.session_state.field_suggestions:
                            continue_after_review()
                        st.rerun()

    message = st.chat_input("Describe your product or answer the question...",
                            disabled=bool(st.session_state.field_suggestions))
    if message:
        say("user", message)
        st.session_state.intake_started = True
        with st.spinner("Gemini is analyzing your response..."):
            try:
                extracted = extract_questionnaire_fields(
                    user_message=message,
                    confirmed_answers=bridge.get_product_profile(),
                    target_field_id=st.session_state.asked_field,
                    target_question=st.session_state.asked_question,
                )
                if extracted:
                    st.session_state.field_suggestions.update(extracted)
                    say("assistant", f"I identified {len(extracted)} potential questionnaire "
                        "answer(s). Please review and confirm them below.")
                elif st.session_state.asked_field is not None:
                    # The answer was not captured; keep the field in focus.
                    ask_field(st.session_state.asked_field, clarification=True)
                else:
                    say("assistant", "I couldn't identify a supported questionnaire answer. "
                        "Could you provide more detail about your product?")
            except Exception as error:
                say("assistant", "I couldn't process that response. Please try again.")
                st.error(str(error))
        st.rerun()

with manual_tab:
    st.header("D2.1 Product and Intended-Use Profile")
    st.caption("Manually enter or correct answers. Only active conditional fields appear.")
    fields = list(bridge.field_labels.items())
    for field_id in bridge.get_active_conditional_fields():
        if field_id not in bridge.field_labels:
            fields.append((field_id, bridge.get_field_label(field_id)))
    for field_id, label in fields:
        field_type = bridge.get_field_type(field_id)
        current = bridge.get_product_profile().get(field_id)
        with st.expander(f"{field_id} — {label}"):
            key = f"manual_{field_id}_{st.session_state.editor_version}"
            if field_type == "text":
                value = st.text_area(label, value=current or "", key=key)
            elif field_type == "selectbox":
                options = bridge.get_field_options(field_id)
                value = st.selectbox(label, ["Select an option"] + options,
                                     index=options.index(current) + 1 if current in options else 0,
                                     key=key)
            elif field_type == "multiselect":
                value = st.multiselect(label, bridge.get_field_options(field_id),
                                       default=current or [], key=key)
            else:
                continue
            if st.button("Save Answer", key=f"save_manual_{field_id}"):
                if value == "Select an option":
                    st.warning("Please select an answer.")
                else:
                    valid, error = bridge.save_answer(field_id, value)
                    if valid:
                        st.session_state.editor_version += 1
                        st.session_state.field_suggestions.pop(field_id, None)
                        # Do not silently skip a pending question; continue once review is clear.
                        if st.session_state.intake_started and not st.session_state.field_suggestions:
                            continue_after_review()
                        st.rerun()
                    else:
                        st.error(error)

st.divider()
with st.expander("View Confirmed D2.1 Profile"):
    st.json(bridge.get_product_profile())
