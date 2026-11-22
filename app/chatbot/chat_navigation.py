"""Conversation footer presentation for Chat Buddy's existing flows."""

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
