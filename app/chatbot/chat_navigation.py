"""Conversation footer presentation for Chat Buddy's existing flows."""

import re

import streamlit as st


def render_section_footer(section, gaps, *, context, next_section=None, resume=None, resume_hint=None):
    """Render the current status and return whether the user chose to advance."""
    with st.container():
        if gaps:
            with st.chat_message("assistant"):
                st.write(f"{section} has unresolved questions or requirements.")
                for gap in gaps[:3]:
                    st.write(f"- {gap}")
                if len(gaps) > 3:
                    st.caption(f"{len(gaps) - 3} more gaps remain.")
            if next_section and st.button(
                "Continue with gaps", key=f"section-next-{context}",
                help=f"Continue to {next_section} and keep this section incomplete.",
            ):
                return True
            if resume:
                if resume_hint:
                    st.caption(resume_hint)
                if st.button("Resume unanswered questions", key=f"section-resume-{context}"):
                    if resume() is not False:
                        st.rerun()
        else:
            with st.chat_message("assistant"):
                st.write(f"{section} complete. All applicable required answers are confirmed.")
            if next_section and st.button(f"Continue to {next_section}", key=f"section-next-{context}"):
                return True
    return False


def conversational_question(prompt):
    """Keep internal questionnaire references in the technical controls."""
    reference = r"\b(?:ACC|DEP|PIP|AIF)-\d+(?:-[A-Z]+)?\b"
    prompt = re.sub(rf"\s*\([^()]*(?:{reference})[^()]*\)", "", prompt)
    prompt = re.sub(reference, "the earlier questionnaire", prompt).strip()
    if re.match(r"^(?:how|what|which|when|where|why|who|do|does|did|is|are|was|were|can|has|have|will)\b", prompt, re.I):
        return prompt
    return f"What should I record about {prompt[:1].lower() + prompt[1:].rstrip('.?')}?"


def unknown_option(kind, options):
    if "Unknown" in options:
        if kind in {"select", "dropdown"}:
            return "Unknown"
        if kind == "multiselect":
            return ["Unknown"]
    return None


def render_record_proposal(key, question, *, algorithm=False):
    """Collect an identity draft from chat. Only return it after confirmation."""
    state = st.session_state
    with st.chat_message("assistant"):
        st.write(question)
    message = st.chat_input("Describe the new record", key=f"{key}-message", max_chars=8000)
    if message and message.strip():
        text = message.strip()
        identity = text.splitlines()[0]
        identity = re.sub(
            r"^(?:our |my |the )?(?:algorithm|model|dataset|evaluation|document)(?: name)? (?:is called|is|called)\s+",
            "", identity, flags=re.I,
        ).strip()
        version = ""
        if algorithm:
            match = re.fullmatch(r"(.+?)[, ]+(?:version\s*|v)([\w.-]+)[.!]?", identity, re.I)
            if match:
                identity, version = match[1].strip(), match[2].rstrip(".")
        generation = state.get("ux_record_proposal_generation", 0) + 1
        state.ux_record_proposal_generation = generation
        state[key] = (text, identity, version, generation)
        st.rerun()
    if key not in state:
        return None
    text, proposed_name, proposed_version, draft_id = state[key]
    with st.chat_message("user"):
        st.text(text)
    with st.form(f"{key}-confirm-form-{draft_id}"):
        name = st.text_input("Record name", value=proposed_name, key=f"{key}-name-{draft_id}")
        version = (
            st.text_input("Record version", value=proposed_version, key=f"{key}-version-{draft_id}") if algorithm else ""
        )
        confirm = st.form_submit_button("Confirm algorithm record" if algorithm else "Confirm new record")
    if not confirm:
        return None
    if not name.strip():
        st.error("Enter a name for the record.")
        return None
    state.pop(key)
    return name.strip(), version.strip(), text


def keep_record_drafts(conversations, previous_id, record_id, review_prefix, manual_prefix, *, revision=None):
    """Retain field inputs when switching records without retaining action clicks."""
    state = st.session_state
    if previous_id != record_id and previous_id in conversations:
        prefixes = (f"{review_prefix}{previous_id}-", f"{manual_prefix}{previous_id}-")
        drafts = {
            key: state[key] for key in state
            if key.startswith(prefixes) and not key.endswith(("-confirm", "-reject", "-skip"))
        }
        if drafts:
            conversations[previous_id]["widget_drafts"] = drafts
    if record_id in conversations:
        drafts = conversations[record_id].pop("widget_drafts", {})
        if revision is not None:
            prefix = re.escape(f"{manual_prefix}{record_id}-")
            drafts = {
                re.sub(rf"^({prefix}ACC-\d+)-\d+(?=-|$)", rf"\g<1>-{revision}", key): value
                for key, value in drafts.items()
            }
        state.update(drafts)
