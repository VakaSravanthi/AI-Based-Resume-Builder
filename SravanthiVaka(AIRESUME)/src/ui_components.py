from __future__ import annotations

from typing import List, Tuple

import plotly.graph_objects as go
import streamlit as st


def show_workflow_diagram(fig: go.Figure) -> None:
    st.subheader("Workflow Visualization")
    st.plotly_chart(fig, use_container_width=True)


def show_agent_outputs(outputs: List[Tuple[str, dict]]) -> None:
    with st.expander("Agent Outputs", expanded=False):
        for name, data in outputs:
            st.markdown(f"**{name}**")
            st.json(data)


def show_match_summary(score: float, confidence: float, missing_skills: List[str], explanation: str, top_snippets: List[Tuple[str, float]]) -> None:
    st.subheader("Results")
    cols = st.columns(3)
    cols[0].metric("Match Score", f"{score:.1f}%")
    cols[1].metric("Confidence", f"{confidence:.2f}")
    cols[2].metric("Top Snippets", f"{len(top_snippets)}")

    if missing_skills:
        st.markdown("**Skill Gaps**: " + ", ".join(missing_skills))
    st.markdown("**Explanation**")
    st.write(explanation)

    if top_snippets:
        st.markdown("**Top Matching Snippets**")
        for text, sim in top_snippets[:5]:
            st.write(f"{sim:.2f} — {text}")
