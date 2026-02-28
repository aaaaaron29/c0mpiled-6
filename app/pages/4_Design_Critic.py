"""Experiment Design Critic page."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, severity_badge, badge, COLORS, inject_css, render_project_sidebar
from src.paper_ingestion import ingest_paper, truncate_paper
from src.search_widget import render_search_widget, search_results_to_papers
from src.llm_utils import call_llm, parse_llm_json
from src.config import get_config

st.set_page_config(page_title="Design Critic — ResearchOS", page_icon="🧪", layout="wide")

page_header("Experiment Design Critic", "Paste your experimental design — hypothesis, variables, controls, sample size, and methodology — to get specific, grounded critique before you run it.", "🧪")

config = get_config()
inject_css()
active_project = render_project_sidebar()

# Input: experiment description
experiment_text = st.text_area(
    "Describe Your Experiment",
    height=200,
    placeholder=(
        "Describe your experimental setup: hypothesis, independent/dependent variables, "
        "control conditions, sample size, methodology, measurement instruments, etc."
    )
)

# Optional: background papers — search or upload
st.markdown("**Optional: Background Papers**")
tab_search, tab_upload = st.tabs(["🔍 Search Papers", "📄 Upload PDFs"])

with tab_search:
    selected_search = render_search_widget(key="page_7_search", min_select=1)

with tab_upload:
    uploaded_papers = st.file_uploader(
        "Optional: Upload background papers (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
    )

if st.button("Critique Design", type="primary", use_container_width=True):
    if not experiment_text.strip():
        st.error("Please describe your experiment.")
        st.stop()
    if not config.openai_api_key:
        st.error("OPENAI_API_KEY not set in .env")
        st.stop()

    # Ingest background papers if provided (optional)
    paper_summary = ""
    if selected_search:
        with st.spinner("Fetching background papers..."):
            papers = search_results_to_papers(selected_search)
            for p in papers:
                st.caption(f"✓ {p['title'][:60]}")
        paper_parts = []
        for p in papers:
            excerpt = truncate_paper(p, max_chars=1500)
            paper_parts.append(f"{p['title']}: {excerpt}")
        paper_summary = "\n\n".join(paper_parts)
    elif uploaded_papers:
        papers = []
        with st.spinner("Parsing background papers..."):
            for f in uploaded_papers:
                paper = ingest_paper(f)
                papers.append(paper)
                st.caption(f"✓ {paper['title'][:60]}")
        paper_parts = []
        for p in papers:
            excerpt = truncate_paper(p, max_chars=1500)
            paper_parts.append(f"{p['title']}: {excerpt}")
        paper_summary = "\n\n".join(paper_parts)

    paper_section = f"\n\nBackground Papers:\n{paper_summary}" if paper_summary else ""

    prompt = f"""You are an experiment design reviewer. Critique this proposed experiment for:
1. Potential confounds not controlled for
2. Missing control conditions
3. Methodological choices that contradict established practice
4. Missing elements needed for publication

Be SPECIFIC — every critique must reference something concrete from the experiment description. No generic advice.

Experiment:
{experiment_text}{paper_section}

Return ONLY JSON:
{{
    "confounds": [{{"description": str, "severity": "Critical"|"Major"|"Minor", "grounded_in": str}}],
    "missing_controls": [{{"description": str, "severity": "Critical"|"Major"|"Minor", "grounded_in": str}}],
    "methodological_concerns": [{{"description": str, "severity": "Critical"|"Major"|"Minor", "grounded_in": str}}],
    "literature_gaps": [{{"description": str, "severity": "Critical"|"Major"|"Minor", "grounded_in": str}}],
    "overall_assessment": str
}}"""

    with st.spinner("Critiquing experiment design..."):
        raw = call_llm(prompt, config)
        result = parse_llm_json(raw)

    if not result:
        st.error("Could not parse AI response. Please try again.")
        with st.expander("Raw response"):
            st.text(raw)
        st.stop()

    # Display results
    st.markdown("---")
    st.subheader("Design Critique")

    if result.get("overall_assessment"):
        st.info(result["overall_assessment"])

    # Count critical issues
    all_issues = (
        result.get("confounds", []) +
        result.get("missing_controls", []) +
        result.get("methodological_concerns", []) +
        result.get("literature_gaps", [])
    )
    critical = len([i for i in all_issues if i.get("severity") == "Critical"])
    major = len([i for i in all_issues if i.get("severity") == "Major"])
    minor = len([i for i in all_issues if i.get("severity") == "Minor"])

    cols = st.columns(4)
    with cols[0]: metric_card("Total Issues", len(all_issues))
    with cols[1]: metric_card("Critical", critical, color=COLORS["danger"])
    with cols[2]: metric_card("Major", major, color=COLORS["warning"])
    with cols[3]: metric_card("Minor", minor)

    # Issue sections
    sections = [
        ("Confounds", result.get("confounds", []), "🔴"),
        ("Missing Controls", result.get("missing_controls", []), "🟡"),
        ("Methodological Concerns", result.get("methodological_concerns", []), "🔵"),
        ("Literature Gaps", result.get("literature_gaps", []), "📚"),
    ]

    for section_name, issues, icon in sections:
        if issues:
            st.subheader(f"{icon} {section_name}")
            for issue in sorted(issues, key=lambda x: {"Critical": 0, "Major": 1, "Minor": 2}.get(x.get("severity", "Minor"), 2)):
                sev = issue.get("severity", "Minor")
                with st.expander(f"{severity_badge(sev)} {issue.get('description', '')[:80]}", expanded=(sev == "Critical")):
                    st.markdown(f"**Grounded in:** {issue.get('grounded_in', '')}")
    # Save to Project
    if active_project:
        st.markdown("---")
        if st.button("Save to Project", key="save_critique", use_container_width=True):
            from src.projects import save_artifact
            save_artifact(active_project, "design_critique", f"Critique: {experiment_text[:50]}",
                          {"experiment": experiment_text, "result": result},
                          metadata={"total_issues": len(all_issues), "critical": critical})
            st.success("Saved to project!")
else:
    st.info("Describe your experiment above and click Critique to get specific, grounded feedback.")
