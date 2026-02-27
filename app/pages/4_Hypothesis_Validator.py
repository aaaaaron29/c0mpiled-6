"""Hypothesis Validator page."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, conf_bar, verdict_badge, badge, COLORS, inject_css
from src.paper_ingestion import ingest_paper, truncate_paper
from src.llm_utils import call_llm, parse_llm_json
from src.config import get_config

st.set_page_config(page_title="Hypothesis Validator — ResearchOS", page_icon="🔬", layout="wide")

page_header("Hypothesis Validator", "Evaluate your hypothesis against uploaded research papers.", "🔬")

config = get_config()

# Input
hypothesis = st.text_area(
    "Your Hypothesis",
    height=120,
    placeholder="e.g., 'Transformer models with sparse attention achieve better generalization than dense attention on long sequences.'"
)

uploaded_papers = st.file_uploader(
    "Upload papers (PDF, 3–10 recommended)",
    type=["pdf"],
    accept_multiple_files=True,
)

if st.button("Validate Hypothesis", type="primary", use_container_width=True):
    if not hypothesis.strip():
        st.error("Please enter a hypothesis.")
        st.stop()
    if not uploaded_papers:
        st.error("Please upload at least one paper.")
        st.stop()
    if not config.openai_api_key:
        st.error("OPENAI_API_KEY not set in .env")
        st.stop()

    # Ingest papers
    papers = []
    with st.spinner("Parsing papers..."):
        for f in uploaded_papers:
            paper = ingest_paper(f)
            papers.append(paper)
            st.caption(f"✓ Parsed: {paper['title'][:80]}")

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
else:
    inject_css()
