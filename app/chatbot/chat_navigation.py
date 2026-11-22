"""Conversation footer presentation for Chat Buddy's existing flows."""

import re

import streamlit as st


def render_section_footer(section, gaps, *, context, next_section=None, resume=None, resume_hint=None):
    """Render the current status and return whether the user chose to advance."""
    state = st.session_state
    reviewing_gaps = state.get("ux_review_gaps_context") == context
    with st.container():
        if gaps:
            with st.chat_message("assistant"):
                st.write(f"{section} has unresolved questions or requirements.")
            with st.expander("Review remaining gaps", expanded=reviewing_gaps):
                for gap in gaps:
                    st.write(f"- {gap}")
            if next_section:
                if reviewing_gaps and st.button(
                    "Confirm continue with gaps", key=f"section-confirm-next-{context}",
                ):
                    state.pop("ux_review_gaps_context", None)
                    return True
                if not reviewing_gaps and st.button(
                    "Continue with gaps", key=f"section-next-{context}",
                    help=f"Review the remaining gaps before continuing to {next_section}.",
                ):
                    state.ux_review_gaps_context = context
                    st.rerun()
            if resume:
                if resume_hint:
                    st.caption(resume_hint)
                if st.button("Resume unanswered questions", key=f"section-resume-{context}"):
                    state.pop("ux_review_gaps_context", None)
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


def propose_record_identity(message, *, algorithm=False, include_version=True):
    """Recognize a short identity statement without consuming its description."""
    first = re.split(r"(?<=[.!?])\s+|[\r\n]+", message.strip(), maxsplit=1)[0].rstrip(".!?")
    named = re.match(
        r"^(?:(?:our|my|the)\s+)?(?:algorithm|model|dataset|evaluation|(?:supporting )?document|report)"
        r"(?:\s+(?:name|title))?\s+(?:is called|is named|is titled|is|called|entitled)\s+",
        first, re.I,
    )
    identity = first[named.end():].strip() if named else first
    match = re.fullmatch(
        r"(.+?)(?:[, ]+|\s*\()(?:version\s*[:=]?\s*|v\s*)(\d[\w.-]*)\)?",
        identity, re.I,
    )
    version = ""
    if match:
        identity, version = match[1].strip(), match[2]
    elif ambiguous := re.search(r"[, (]+version\b(?=\s|[:=]|$)", identity, re.I):
        identity = identity[:ambiguous.start()].strip()
    # Leave the proposal blank when the initial sentence reads like a
    # description or several possible names instead of a single identity.
    if len(identity) > 120 or re.search(
        r"[,;:]|\b(?:either|or|maybe|possibly|unsure|unknown|uses?|contains?|includes?|"
        r"detects?|analy[sz]es?|evaluates?|compares?|measures?|process(?:es)?|supports?|"
        r"has|have|is|are|was|were|will)\b"
        r"|^(?:a|an|i|we|it|they|this|yes|no)\b",
        identity, re.I,
    ):
        return "", ""
    if version and not algorithm and include_version:
        identity = f"{identity}, version {version}"
    return identity, version if algorithm else ""


def render_record_proposal(key, question, *, algorithm=False, include_version=True):
    """Collect an identity draft from chat. Only return it after confirmation."""
    state = st.session_state
    with st.chat_message("assistant"):
        st.write(question)
    message = st.chat_input("Describe the new record", key=f"{key}-message", max_chars=8000)
    if message and message.strip():
        identity, version = propose_record_identity(message, algorithm=algorithm, include_version=include_version)
        generation = state.get("ux_record_proposal_generation", 0) + 1
        state.ux_record_proposal_generation = generation
        state[key] = (message, identity, version, generation)
        st.rerun()
    if key not in state:
        return None
    text, proposed_name, proposed_version, draft_id = state[key]
    with st.chat_message("user"):
        st.text(text)
    if not proposed_name or (algorithm and not proposed_version):
        st.caption("Review the proposed identity. Enter the name and any version you can confirm.")
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
