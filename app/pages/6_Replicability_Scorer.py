"""Methods Replicability Scorer page."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, conf_bar, badge, COLORS, inject_css
from src.paper_ingestion import ingest_paper
from src.search_widget import render_search_widget, search_results_to_papers
from src.llm_utils import call_llm, parse_llm_json
from src.config import get_config

st.set_page_config(page_title="Replicability Scorer — ResearchOS", page_icon="📊", layout="wide")

page_header("Replicability Scorer", "Score a paper's methods section for reproducibility.", "📊")

config = get_config()

# Paper input — search or upload
tab_search, tab_upload = st.tabs(["🔍 Search Papers", "📄 Upload PDFs"])

with tab_search:
    selected_search = render_search_widget(key="page_6_search", min_select=1)

with tab_upload:
    uploaded = st.file_uploader("Upload one paper (PDF)", type=["pdf"])

if st.button("Score Replicability", type="primary", use_container_width=True):
    if not config.openai_api_key:
        st.error("OPENAI_API_KEY not set in .env")
        st.stop()

    # Ingest paper from whichever source is populated
    paper = None
    if selected_search:
        with st.spinner("Fetching paper..."):
            papers = search_results_to_papers(selected_search[:1])
            if papers:
                paper = papers[0]
                st.caption(f"✓ {paper['title'][:80]}")
    elif uploaded:
        with st.spinner("Parsing paper..."):
            paper = ingest_paper(uploaded)
            st.caption(f"✓ Parsed: {paper['title'][:80]}")

    if not paper:
        st.error("Please search for or upload a paper.")
        st.stop()

    # Use methods section or full text
    methods_text = paper["sections"].get("methods", "") or paper["full_text"]
    methods_text = methods_text[:4000]

    prompt = f"""Evaluate this paper's methods for replicability. Score each criterion 0 (missing), 1 (partial), 2 (complete):

1. Datasets named and cited
2. Hyperparameters/experimental parameters specified
3. Code or data availability (GitHub, DOI, supplementary)
4. Statistical methods described
5. Sample size / dataset size reported
6. Experimental setup detailed enough to reproduce

Paper text:
{methods_text}

Return ONLY JSON:
{{
    "overall_score": <int 0-100>,
    "criteria": [{{"name": str, "score": 0|1|2, "quote_or_note": str}}],
    "critical_gaps": [str],
    "suggestions": [str]
}}"""

    with st.spinner("Scoring replicability..."):
        raw = call_llm(prompt, config)
        result = parse_llm_json(raw)

    if not result:
        st.error("Could not parse AI response. Please try again.")
        with st.expander("Raw response"):
            st.text(raw)
        st.stop()

    # Display results
    st.markdown("---")
    st.subheader(f"Results: {paper['title'][:80]}")

    overall = result.get("overall_score", 0)

    # Overall score — big display
    if overall >= 70:
        color = COLORS["success"]
        grade = "Good"
    elif overall >= 40:
        color = COLORS["warning"]
        grade = "Fair"
    else:
        color = COLORS["danger"]
        grade = "Poor"

    st.markdown(f"""
    <div style="text-align:center; padding:24px; background:{COLORS['card']}; border-radius:16px; margin-bottom:24px;">
        <div style="font-size:4rem; font-weight:700; color:{color};">{overall}</div>
        <div style="color:{COLORS['muted']}; font-size:1.2rem;">/ 100 — {grade} Replicability</div>
    </div>
    """, unsafe_allow_html=True)

    conf_bar(overall, "Replicability Score")

    # Per-criterion breakdown
    st.subheader("Criterion Breakdown")
    criteria = result.get("criteria", [])
    for c in criteria:
        score = c.get("score", 0)
        icon = {0: "❌", 1: "🟡", 2: "✅"}.get(score, "❓")
        color_map = {0: COLORS["danger"], 1: COLORS["warning"], 2: COLORS["success"]}
        note = c.get("quote_or_note", "")
        with st.expander(f"{icon} {c.get('name', '')} — {'Missing' if score==0 else 'Partial' if score==1 else 'Complete'}"):
            if note:
                st.markdown(f"_{note}_")

    # Gaps and suggestions
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Critical Gaps")
        gaps = result.get("critical_gaps", [])
        if gaps:
            for g in gaps:
                st.markdown(f"• {g}")
        else:
            st.caption("No critical gaps identified.")

    with col2:
        st.subheader("Suggestions")
        suggestions = result.get("suggestions", [])
        if suggestions:
            for s in suggestions:
                st.markdown(f"• {s}")
        else:
            st.caption("No suggestions.")
else:
    inject_css()
    st.info("Upload a paper PDF to score its replicability.")
