"""Cross-Paper Contradiction Detector page."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, severity_badge, badge, COLORS, inject_css
from src.paper_ingestion import ingest_paper, truncate_paper
from src.llm_utils import call_llm, parse_llm_json
from src.config import get_config

st.set_page_config(page_title="Contradiction Detector — ResearchOS", page_icon="⚡", layout="wide")

page_header("Contradiction Detector", "Find conflicting claims across multiple research papers.", "⚡")

config = get_config()

uploaded_papers = st.file_uploader(
    "Upload papers (PDF, 5–15 recommended)",
    type=["pdf"],
    accept_multiple_files=True,
)

if st.button("Detect Contradictions", type="primary", use_container_width=True):
    if not uploaded_papers or len(uploaded_papers) < 2:
        st.error("Please upload at least 2 papers.")
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

    # Call 1: Extract claims
    paper_blocks = []
    for p in papers:
        excerpt = truncate_paper(p, max_chars=2000)
        paper_blocks.append(f"Title: {p['title']}\n{excerpt}")
    papers_text = "\n\n---\n\n".join(paper_blocks)

    claim_prompt = f"""Extract the 3-5 strongest empirical claims from each paper below.
For each claim provide: paper_title, claim_text, claim_type (finding/methodology/metric).

Papers:
{papers_text}

Return ONLY JSON: list of {{"paper_title": str, "claims": [{{"text": str, "type": str}}]}}"""

    with st.spinner("Extracting claims from papers (Step 1/2)..."):
        raw_claims = call_llm(claim_prompt, config)
        claims_data = parse_llm_json(raw_claims)

    if not claims_data:
        st.error("Could not extract claims. Please try again.")
        with st.expander("Raw response"):
            st.text(raw_claims)
        st.stop()

    # Flatten claims for display
    all_claims = []
    if isinstance(claims_data, list):
        for paper_entry in claims_data:
            title = paper_entry.get("paper_title", "Unknown")
            for claim in paper_entry.get("claims", []):
                all_claims.append({"paper": title, "claim": claim.get("text", ""), "type": claim.get("type", "")})

    st.info(f"Extracted {len(all_claims)} claims from {len(papers)} papers.")

    # Call 2: Detect contradictions
    claims_text = "\n".join([f"[{c['paper']}] ({c['type']}): {c['claim']}" for c in all_claims])

    contra_prompt = f"""Given these extracted claims, identify pairs that genuinely contradict each other.
Only flag real contradictions (same variable, same context), not superficial differences.

Claims:
{claims_text}

Return ONLY JSON: list of {{"paper_a": str, "paper_b": str, "claim_a": str, "claim_b": str, "severity": "Direct"|"Partial"|"Contextual", "explanation": str}}"""

    with st.spinner("Detecting contradictions (Step 2/2)..."):
        raw_contra = call_llm(contra_prompt, config)
        contradictions = parse_llm_json(raw_contra)

    if not contradictions:
        st.success("No contradictions detected — or could not parse response.")
        with st.expander("Raw response"):
            st.text(raw_contra)
        st.stop()

    if isinstance(contradictions, dict):
        contradictions = [contradictions]

    # Sort by severity
    severity_order = {"Direct": 0, "Partial": 1, "Contextual": 2}
    contradictions = sorted(contradictions, key=lambda x: severity_order.get(x.get("severity", "Contextual"), 2))

    # Display
    st.markdown("---")
    st.subheader("Contradictions Found")

    # Summary metrics
    direct = len([c for c in contradictions if c.get("severity") == "Direct"])
    partial = len([c for c in contradictions if c.get("severity") == "Partial"])
    contextual = len([c for c in contradictions if c.get("severity") == "Contextual"])

    cols = st.columns(4)
    with cols[0]: metric_card("Total", len(contradictions))
    with cols[1]: metric_card("Direct", direct, color=COLORS["danger"])
    with cols[2]: metric_card("Partial", partial, color=COLORS["warning"])
    with cols[3]: metric_card("Contextual", contextual)

    for i, c in enumerate(contradictions):
        sev = c.get("severity", "Contextual")
        with st.expander(f"{severity_badge(sev)} {c.get('paper_a', '?')[:30]} vs {c.get('paper_b', '?')[:30]}", expanded=(sev == "Direct")):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**{c.get('paper_a', '')}**")
                st.markdown(f"_{c.get('claim_a', '')}_")
            with col_b:
                st.markdown(f"**{c.get('paper_b', '')}**")
                st.markdown(f"_{c.get('claim_b', '')}_")
            st.markdown(f"**Explanation:** {c.get('explanation', '')}")

    # Claims table
    with st.expander("All Extracted Claims"):
        import pandas as pd
        st.dataframe(pd.DataFrame(all_claims), use_container_width=True)
else:
    inject_css()
    st.info("Upload 2 or more papers to detect contradictions.")
