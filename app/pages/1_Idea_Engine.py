"""Idea Engine — Research Discovery + Hypothesis Validation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, conf_bar, verdict_badge, badge, COLORS, inject_css, render_project_sidebar
from src.paper_ingestion import ingest_paper, truncate_paper
from src.search_widget import render_search_widget, search_results_to_papers
from src.paper_search import search_papers
from src.llm_utils import call_llm, parse_llm_json
from src.config import get_config

st.set_page_config(page_title="Idea Engine — ResearchOS", page_icon="💡", layout="wide")

page_header("Idea Engine", "Generate novel research ideas or validate a hypothesis against real papers.", "💡")

config = get_config()
inject_css()
active_project = render_project_sidebar()

FEASIBILITY_COLORS = {"High": COLORS["success"], "Medium": COLORS["warning"], "Low": COLORS["danger"]}

mode = st.radio("Mode", ["Research Discovery", "Validate a Hypothesis"], horizontal=True)

# ============================================================
# MODE 1: Research Discovery
# ============================================================
if mode == "Research Discovery":
    prefill = st.session_state.pop("idea_engine_topic", "")
    topic = st.text_input(
        "Enter a research topic or area of interest",
        value=prefill,
        placeholder="e.g. federated learning for medical imaging",
    )

    # Paper input — search or upload
    tab_search, tab_upload = st.tabs(["🔍 Search Papers", "📄 Upload PDFs"])

    with tab_search:
        selected_search = render_search_widget(key="page_4_discovery_search", min_select=1)

    with tab_upload:
        uploaded_papers = st.file_uploader(
            "Upload papers (PDF, 3–10 recommended)",
            type=["pdf"],
            accept_multiple_files=True,
            key="discovery_upload",
        )

    if st.button("Discover Ideas", type="primary", use_container_width=True):
        if not topic.strip():
            st.error("Please enter a research topic.")
            st.stop()
        if not config.openai_api_key:
            st.error("OPENAI_API_KEY not set in .env")
            st.stop()

        # Gather papers: from search widget, upload, or auto-search the topic
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
            # Auto-search: fetch top papers on the topic
            with st.spinner(f"Searching for papers on '{topic}'..."):
                auto_results = search_papers(topic, limit=8)
            if auto_results:
                st.info(f"Auto-found {len(auto_results)} papers. Fetching content...")
                with st.spinner("Downloading papers..."):
                    papers = search_results_to_papers(auto_results)
                    for p in papers:
                        st.caption(f"✓ {p['title'][:80]}")

        if not papers:
            st.error("No papers found. Try a different topic or upload PDFs.")
            st.stop()

        # Build prompt
        paper_blocks = []
        for p in papers:
            excerpt = truncate_paper(p, max_chars=2500)
            paper_blocks.append(f"**{p['title']}**\n{excerpt}")
        papers_text = "\n\n---\n\n".join(paper_blocks)

        prompt = f"""You are a research strategist. Given the topic and paper excerpts below, perform a landscape analysis and generate novel research ideas.

Topic: {topic}

Papers:
{papers_text}

Return ONLY a JSON object (no markdown, no explanation) with:
- themes: list of strings — the 3-6 main themes/findings across the papers
- gaps: list of strings — 3-5 open questions or gaps in the literature
- ideas: list of objects, each with:
  - title: str — concise title for the research idea
  - description: str — one-sentence description of the idea
  - novelty_rationale: str — why this idea is novel given the current literature
  - feasibility: "High" | "Medium" | "Low" — how feasible this is to execute"""

        with st.spinner("Analyzing landscape and generating ideas..."):
            raw = call_llm(prompt, config)
            result = parse_llm_json(raw)

        if not result:
            st.error("Could not parse AI response. Please try again.")
            with st.expander("Raw response"):
                st.text(raw)
            st.stop()

        # ---- Display: Landscape ----
        st.markdown("---")
        st.subheader("Research Landscape")

        themes = result.get("themes", [])
        if themes:
            st.markdown("**Key Themes**")
            cols = st.columns(min(len(themes), 3))
            for i, theme in enumerate(themes):
                with cols[i % len(cols)]:
                    st.markdown(f"""
                    <div class="metric-card" style="min-height:60px;">
                        <div style="font-size:0.9rem;">{theme}</div>
                    </div>
                    """, unsafe_allow_html=True)

        gaps = result.get("gaps", [])
        if gaps:
            st.markdown("**Open Questions & Gaps**")
            for g in gaps:
                st.markdown(f"- {g}")

        # ---- Display: Research Ideas ----
        ideas = result.get("ideas", [])
        if ideas:
            st.markdown("---")
            st.subheader(f"Research Ideas ({len(ideas)})")

            for idx, idea in enumerate(ideas):
                feasibility = idea.get("feasibility", "Medium")
                f_color = FEASIBILITY_COLORS.get(feasibility, COLORS["neutral"])
                f_badge = badge(feasibility, f_color)

                st.markdown(f"""
                <div class="tool-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h3 style="margin:0; font-size:1.1rem;">{idea.get('title', '')}</h3>
                        <span>{f_badge}</span>
                    </div>
                    <p style="color:{COLORS['text']}; margin:8px 0 4px 0;">{idea.get('description', '')}</p>
                    <p style="color:{COLORS['muted']}; font-size:0.85rem; margin:0;">
                        <strong>Why novel:</strong> {idea.get('novelty_rationale', '')}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"→ Build Roadmap", key=f"roadmap_{idx}"):
                    st.session_state["roadmap_topic"] = idea.get("title", "")
                    st.switch_page("pages/2_Research_Roadmap.py")

        st.caption(f"Based on {len(papers)} papers.")

        # Save to Project
        if active_project:
            st.markdown("---")
            if st.button("Save to Project", key="save_discovery", use_container_width=True):
                from src.projects import save_artifact
                save_artifact(active_project, "topic_exploration", f"Discovery: {topic[:50]}",
                              {"topic": topic, "result": result, "paper_count": len(papers)},
                              metadata={"mode": "discovery", "topic": topic})
                st.success("Saved to project!")

# ============================================================
# MODE 2: Hypothesis Validation (existing logic, unchanged)
# ============================================================
else:
    hypothesis = st.text_area(
        "Your Hypothesis",
        height=120,
        placeholder="e.g., 'Transformer models with sparse attention achieve better generalization than dense attention on long sequences.'"
    )

    # Paper input — search or upload
    tab_search, tab_upload = st.tabs(["🔍 Search Papers", "📄 Upload PDFs"])

    with tab_search:
        selected_search = render_search_widget(key="page_4_validate_search", min_select=1)

    with tab_upload:
        uploaded_papers = st.file_uploader(
            "Upload papers (PDF, 3–10 recommended)",
            type=["pdf"],
            accept_multiple_files=True,
            key="validate_upload",
        )

    if st.button("Validate Hypothesis", type="primary", use_container_width=True):
        if not hypothesis.strip():
            st.error("Please enter a hypothesis.")
            st.stop()
        if not config.openai_api_key:
            st.error("OPENAI_API_KEY not set in .env")
            st.stop()

        # Ingest papers from whichever source is populated
        papers = []
        if selected_search:
            with st.spinner("Fetching papers..."):
                papers = search_results_to_papers(selected_search)
                for p in papers:
                    st.caption(f"✓ {p['title'][:80]}")
        elif uploaded_papers:
            with st.spinner("Parsing papers..."):
                for f in uploaded_papers:
                    paper = ingest_paper(f)
                    papers.append(paper)
                    st.caption(f"✓ Parsed: {paper['title'][:80]}")

        if not papers:
            st.error("Please search for or upload at least one paper.")
            st.stop()

        # Build prompt
        paper_blocks = []
        for p in papers:
            excerpt = truncate_paper(p, max_chars=3000)
            paper_blocks.append(f"**{p['title']}**\n{excerpt}")
        papers_text = "\n\n---\n\n".join(paper_blocks)

        prompt = f"""You are a research hypothesis validator. Given the hypothesis and paper excerpts below, evaluate the hypothesis.

Hypothesis: {hypothesis}

Papers:
{papers_text}

Return ONLY a JSON object (no markdown, no explanation) with:
- support_score (0.0-1.0)
- novelty_score (0.0-1.0)
- feasibility_score (0.0-1.0)
- supporting_evidence: list of {{"paper_title": str, "quote": str, "relevance": str}}
- contradicting_evidence: list of {{"paper_title": str, "quote": str, "relevance": str}}
- verdict: one of "Strong", "Weak", "Contradicted", "Ungrounded"
- summary: 2-3 sentence explanation"""

        with st.spinner("Validating hypothesis with AI..."):
            raw = call_llm(prompt, config)
            result = parse_llm_json(raw)

        if not result:
            st.error("Could not parse AI response. Please try again.")
            with st.expander("Raw response"):
                st.text(raw)
            st.stop()

        # Display results
        st.markdown("---")
        st.subheader("Validation Results")

        # Verdict
        verdict = result.get("verdict", "Unknown")
        st.markdown(f"### Verdict: {verdict_badge(verdict)}", unsafe_allow_html=True)

        if result.get("summary"):
            st.info(result["summary"])

        # Scores
        cols = st.columns(3)
        with cols[0]:
            score = int(result.get("support_score", 0) * 100)
            metric_card("Support", f"{score}%")
            conf_bar(score)
        with cols[1]:
            score = int(result.get("novelty_score", 0) * 100)
            metric_card("Novelty", f"{score}%")
            conf_bar(score)
        with cols[2]:
            score = int(result.get("feasibility_score", 0) * 100)
            metric_card("Feasibility", f"{score}%")
            conf_bar(score)

        # Evidence tables
        col_sup, col_con = st.columns(2)

        with col_sup:
            st.subheader("Supporting Evidence")
            sup = result.get("supporting_evidence", [])
            if sup:
                for ev in sup:
                    with st.expander(f"📄 {ev.get('paper_title', '')[:50]}"):
                        st.markdown(f"**Quote:** _{ev.get('quote', '')}_")
                        st.markdown(f"**Relevance:** {ev.get('relevance', '')}")
            else:
                st.caption("No supporting evidence found.")

        with col_con:
            st.subheader("Contradicting Evidence")
            con = result.get("contradicting_evidence", [])
            if con:
                for ev in con:
                    with st.expander(f"⚠️ {ev.get('paper_title', '')[:50]}"):
                        st.markdown(f"**Quote:** _{ev.get('quote', '')}_")
                        st.markdown(f"**Relevance:** {ev.get('relevance', '')}")
            else:
                st.caption("No contradicting evidence found.")

        # Save to Project
        if active_project:
            st.markdown("---")
            if st.button("Save to Project", key="save_validation", use_container_width=True):
                from src.projects import save_artifact
                save_artifact(active_project, "hypothesis_validation", f"Hypothesis: {hypothesis[:50]}",
                              {"hypothesis": hypothesis, "result": result, "paper_count": len(papers)},
                              metadata={"mode": "validation", "verdict": result.get("verdict", "")})
                st.success("Saved to project!")
