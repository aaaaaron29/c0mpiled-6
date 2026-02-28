"""Literature Lens — Understand debates, gaps, and open questions in any research area."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, badge, COLORS, inject_css, render_project_sidebar
from src.paper_ingestion import ingest_paper, truncate_paper
from src.search_widget import render_search_widget, search_results_to_papers
from src.paper_search import search_papers
from src.llm_utils import call_llm, parse_llm_json
from src.config import get_config

st.set_page_config(page_title="Literature Lens — ResearchOS", page_icon="🔎", layout="wide")

page_header("Literature Lens", "Understand the debates, gaps, and open questions in any research area.", "🔎")

config = get_config()
inject_css()
active_project = render_project_sidebar()

INTENSITY_COLORS = {"Active": COLORS["danger"], "Moderate": COLORS["warning"], "Settled": COLORS["success"]}

# ---- Input ----
topic = st.text_input(
    "Enter a research topic or area of interest",
    placeholder="e.g. explainable AI in healthcare",
)

# Paper input — search or upload
tab_search, tab_upload = st.tabs(["🔍 Search Papers", "📄 Upload PDFs"])

with tab_search:
    selected_search = render_search_widget(key="page_5_lens_search", min_select=2)

with tab_upload:
    uploaded_papers = st.file_uploader(
        "Upload papers (PDF, 4–10 recommended)",
        type=["pdf"],
        accept_multiple_files=True,
        key="lens_upload",
    )

if st.button("Analyze Literature", type="primary", use_container_width=True):
    if not topic.strip():
        st.error("Please enter a research topic.")
        st.stop()
    if not config.openai_api_key:
        st.error("OPENAI_API_KEY not set in .env")
        st.stop()

    # Gather papers
    papers = []
    if selected_search:
        with st.spinner("Fetching selected papers..."):
            papers = search_results_to_papers(selected_search)
            for p in papers:
                st.caption(f"✓ {p['title'][:80]}")
    elif uploaded_papers:
        with st.spinner("Parsing papers..."):
            for f in uploaded_papers:
                paper = ingest_paper(f)
                papers.append(paper)
                st.caption(f"✓ Parsed: {paper['title'][:80]}")
    else:
        # Auto-search the topic
        with st.spinner(f"Searching for papers on '{topic}'..."):
            auto_results = search_papers(topic, limit=8)
        if auto_results:
            st.info(f"Auto-found {len(auto_results)} papers. Fetching content...")
            with st.spinner("Downloading papers..."):
                papers = search_results_to_papers(auto_results)
                for p in papers:
                    st.caption(f"✓ {p['title'][:80]}")

    if len(papers) < 2:
        st.error("Need at least 2 papers. Try a different topic or upload PDFs.")
        st.stop()

    # Build paper context
    paper_blocks = []
    for p in papers:
        excerpt = truncate_paper(p, max_chars=2000)
        paper_blocks.append(f"Title: {p['title']}\n{excerpt}")
    papers_text = "\n\n---\n\n".join(paper_blocks)

    prompt = f"""You are a research literature analyst. Given the topic and paper excerpts below, provide a comprehensive analysis of the debates, consensus, gaps, and emerging directions in this research area.

Topic: {topic}

Papers:
{papers_text}

Return ONLY a JSON object (no markdown, no explanation) with:
- field_consensus: 2-3 sentence summary of what the literature broadly agrees on
- contested_claims: list of {{"claim": str, "side_a": {{"position": str, "papers": [str]}}, "side_b": {{"position": str, "papers": [str]}}, "why_it_matters": str}}
- open_questions: list of {{"question": str, "context": str, "opportunity": str}}
- methodological_inconsistencies: list of {{"issue": str, "impact": str}}
- emerging_directions: list of {{"direction": str, "evidence": str}}
- debate_intensity: "Active"|"Moderate"|"Settled" """

    with st.spinner("Analyzing literature landscape..."):
        raw = call_llm(prompt, config)
        result = parse_llm_json(raw)

    if not result:
        st.error("Could not parse AI response. Please try again.")
        with st.expander("Raw response"):
            st.text(raw)
        st.stop()

    # ---- Display ----
    st.markdown("---")

    # Top row: metric cards
    intensity = result.get("debate_intensity", "Moderate")
    i_color = INTENSITY_COLORS.get(intensity, COLORS["neutral"])
    open_qs = result.get("open_questions", [])

    cols = st.columns(2)
    with cols[0]:
        metric_card("Debate Intensity", intensity, color=i_color)
    with cols[1]:
        metric_card("Open Questions", len(open_qs), color=COLORS["primary"])

    # Field Consensus
    consensus = result.get("field_consensus", "")
    if consensus:
        st.subheader("Field Consensus")
        st.info(consensus)

    # Contested Claims
    contested = result.get("contested_claims", [])
    if contested:
        st.subheader("Contested Claims")
        for claim in contested:
            side_a = claim.get("side_a", {})
            side_b = claim.get("side_b", {})
            a_papers = " ".join([badge(p[:40], COLORS["primary"]) for p in side_a.get("papers", [])])
            b_papers = " ".join([badge(p[:40], COLORS["warning"]) for p in side_b.get("papers", [])])
            st.markdown(f"""
            <div class="tool-card">
                <h3 style="margin:0 0 12px 0; font-size:1.05rem;">{claim.get('claim', '')}</h3>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                    <div>
                        <div style="color:{COLORS['success']}; font-weight:600; font-size:0.85rem; margin-bottom:6px;">SIDE A</div>
                        <p style="color:{COLORS['text']}; font-size:0.9rem; margin:0 0 8px 0;">{side_a.get('position', '')}</p>
                        <div>{a_papers}</div>
                    </div>
                    <div>
                        <div style="color:{COLORS['danger']}; font-weight:600; font-size:0.85rem; margin-bottom:6px;">SIDE B</div>
                        <p style="color:{COLORS['text']}; font-size:0.9rem; margin:0 0 8px 0;">{side_b.get('position', '')}</p>
                        <div>{b_papers}</div>
                    </div>
                </div>
                <p style="color:{COLORS['muted']}; font-size:0.85rem; margin:12px 0 0 0; border-top:1px solid {COLORS['border']}; padding-top:8px;">
                    <strong>Why it matters:</strong> {claim.get('why_it_matters', '')}
                </p>
            </div>
            """, unsafe_allow_html=True)

    # Open Questions
    if open_qs:
        st.subheader("Open Questions")
        q_cols = st.columns(2)
        for idx, q in enumerate(open_qs):
            with q_cols[idx % 2]:
                opp_badge = badge("Opportunity", COLORS["success"])
                st.markdown(f"""
                <div class="metric-card">
                    <h4 style="margin:0 0 8px 0; font-size:0.95rem;">{q.get('question', '')}</h4>
                    <p style="color:{COLORS['muted']}; font-size:0.85rem; margin:0 0 8px 0;">{q.get('context', '')}</p>
                    <div>{opp_badge} <span style="color:{COLORS['text']}; font-size:0.85rem;">{q.get('opportunity', '')}</span></div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"→ Explore in Idea Engine", key=f"idea_{idx}"):
                    st.session_state["idea_engine_topic"] = q.get("question", "")
                    st.switch_page("pages/1_Idea_Engine.py")

    # Methodological Inconsistencies
    method_issues = result.get("methodological_inconsistencies", [])
    if method_issues:
        st.subheader("Methodological Inconsistencies")
        for m in method_issues:
            st.markdown(f"""
            <div class="trace-step">
                <strong>{m.get('issue', '')}</strong>
                <div style="margin-top:4px; color:{COLORS['muted']}; font-size:0.85rem;">Impact: {m.get('impact', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    # Emerging Directions
    directions = result.get("emerging_directions", [])
    if directions:
        st.subheader("Emerging Directions")
        for d in directions:
            st.markdown(f"""
            <div class="tool-card">
                <h4 style="margin:0 0 6px 0; font-size:0.95rem;">{d.get('direction', '')}</h4>
                <p style="color:{COLORS['muted']}; font-size:0.85rem; margin:0;">{d.get('evidence', '')}</p>
            </div>
            """, unsafe_allow_html=True)

    st.caption(f"Based on {len(papers)} papers.")

    # Save to Project
    if active_project:
        st.markdown("---")
        if st.button("Save to Project", key="save_lens", use_container_width=True):
            from src.projects import save_artifact
            save_artifact(active_project, "literature_analysis", f"Literature: {topic[:50]}",
                          {"topic": topic, "result": result, "paper_count": len(papers)},
                          metadata={"topic": topic, "debate_intensity": result.get("debate_intensity", "")})
            st.success("Saved to project!")
else:
    inject_css()
    st.info("Enter a research topic above and click Analyze to understand the debates, gaps, and open questions in the field.")
