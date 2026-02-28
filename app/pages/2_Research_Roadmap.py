"""Research Roadmap — Turn a research interest into an actionable project plan."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, badge, trace_step, COLORS, inject_css, render_project_sidebar
from src.paper_search import search_papers
from src.search_widget import search_results_to_papers
from src.paper_ingestion import truncate_paper
from src.llm_utils import call_llm, parse_llm_json
from src.config import get_config

st.set_page_config(page_title="Research Roadmap — ResearchOS", page_icon="🗺️", layout="wide")

page_header("Research Roadmap", "Turn a research interest into an actionable project plan.", "🗺️")

inject_css()
config = get_config()
active_project = render_project_sidebar()

COMPLEXITY_COLORS = {"Beginner": COLORS["success"], "Intermediate": COLORS["warning"], "Advanced": COLORS["danger"]}
ACCESS_COLORS = {"Free": COLORS["success"], "Restricted": COLORS["warning"], "Paid": COLORS["danger"]}

# ---- Step 1: Topic Input ----
prefill = st.session_state.pop("roadmap_topic", "")
auto_run = bool(prefill)

topic = st.text_input(
    "What topic do you want to research?",
    value=prefill,
    placeholder="e.g. graph neural networks for drug discovery",
)

constraints = st.text_input(
    "Any constraints? (optional)",
    placeholder="e.g. semester timeframe, no GPU access, undergraduate level",
)

if st.button("Find Papers & Build Roadmap", type="primary", use_container_width=True) or auto_run:
    if not topic.strip():
        st.error("Please enter a research topic.")
        st.stop()
    if not config.openai_api_key:
        st.error("OPENAI_API_KEY not set in .env")
        st.stop()

    # ---- Step 2: Paper Discovery (automatic) ----
    with st.spinner("Searching literature..."):
        search_results = search_papers(topic, limit=6)

    if search_results:
        papers = []
        with st.spinner("Fetching paper content..."):
            papers = search_results_to_papers(search_results)

        st.markdown("**Literature found:**")
        for p in papers:
            year = ""
            # Try to get year from search results
            matching = [s for s in search_results if s["title"] == p["title"]]
            if matching and matching[0].get("year"):
                year = f" ({matching[0]['year']})"
            st.caption(f"• {p['title'][:90]}{year}")
    else:
        papers = []
        st.warning("No papers found via search. Generating roadmap from topic alone.")

    # ---- Step 3: Roadmap Generation ----
    paper_context = ""
    if papers:
        paper_blocks = []
        for p in papers:
            excerpt = truncate_paper(p, max_chars=1500)
            paper_blocks.append(f"{p['title']}: {excerpt}")
        paper_context = "\n\n".join(paper_blocks)

    constraints_block = f"\nConstraints: {constraints}" if constraints.strip() else ""

    prompt = f"""You are a research planning advisor. Given the topic, constraints, and relevant paper excerpts, create a comprehensive research roadmap for someone starting in this area.

Topic: {topic}{constraints_block}

{"Papers:" + chr(10) + paper_context if paper_context else "No specific papers available — use your knowledge of this research area."}

Return ONLY a JSON object (no markdown, no explanation) with:
- complexity: "Beginner"|"Intermediate"|"Advanced" — overall difficulty of this research area
- complexity_rationale: one sentence explanation
- prerequisites: list of strings — skills/knowledge needed before starting
- landscape_summary: 2-3 sentence summary of the current state of this research area
- suggested_datasets: list of {{"name": str, "description": str, "url": str, "accessibility": "Free"|"Restricted"|"Paid"}}
- methodology_steps: list of {{"step": int, "title": str, "description": str, "estimated_time": str}}
- related_benchmarks: list of strings
- entry_point_papers: list of strings — paper titles good for getting started
- research_angles: list of {{"title": str, "description": str, "good_for": "Beginner"|"Intermediate"|"Advanced"}}"""

    with st.spinner("Building your research roadmap..."):
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
    complexity = result.get("complexity", "Intermediate")
    c_color = COMPLEXITY_COLORS.get(complexity, COLORS["neutral"])
    datasets = result.get("suggested_datasets", [])
    steps = result.get("methodology_steps", [])

    cols = st.columns(3)
    with cols[0]:
        metric_card("Complexity", complexity, color=c_color)
    with cols[1]:
        metric_card("Datasets", len(datasets))
    with cols[2]:
        metric_card("Methodology Steps", len(steps))

    if result.get("complexity_rationale"):
        st.caption(result["complexity_rationale"])

    # Landscape Summary
    st.subheader("Current State of the Field")
    st.info(result.get("landscape_summary", ""))

    # Prerequisites
    prereqs = result.get("prerequisites", [])
    if prereqs:
        st.subheader("Prerequisites")
        prereq_html = " ".join([badge(p, COLORS["primary"]) for p in prereqs])
        st.markdown(prereq_html, unsafe_allow_html=True)

    # Methodology Steps
    if steps:
        st.subheader("Methodology")
        for s in sorted(steps, key=lambda x: x.get("step", 0)):
            step_num = s.get("step", "?")
            title = s.get("title", "")
            desc = s.get("description", "")
            time_est = s.get("estimated_time", "")
            trace_step(
                f"Step {step_num}: {title}",
                time_est,
                desc,
                "success" if step_num == 1 else "",
            )

    # Suggested Datasets
    if datasets:
        st.subheader("Suggested Datasets")
        ds_cols = st.columns(2)
        for i, ds in enumerate(datasets):
            with ds_cols[i % 2]:
                access = ds.get("accessibility", "Free")
                a_color = ACCESS_COLORS.get(access, COLORS["neutral"])
                a_badge = badge(access, a_color)
                url = ds.get("url", "")
                url_html = f'<a href="{url}" target="_blank" style="color:{COLORS["primary"]}; font-size:0.85rem;">Link</a>' if url and url.startswith("http") else ""
                st.markdown(f"""
                <div class="metric-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong>{ds.get('name', '')}</strong>
                        <span>{a_badge}</span>
                    </div>
                    <p style="color:{COLORS['muted']}; font-size:0.85rem; margin:6px 0 4px 0;">{ds.get('description', '')}</p>
                    {url_html}
                </div>
                """, unsafe_allow_html=True)

    # Research Angles
    angles = result.get("research_angles", [])
    if angles:
        st.subheader("Research Angles")
        for angle in angles:
            gf = angle.get("good_for", "Intermediate")
            gf_color = COMPLEXITY_COLORS.get(gf, COLORS["neutral"])
            gf_badge = badge(f"Good for: {gf}", gf_color)
            st.markdown(f"""
            <div class="tool-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; font-size:1.05rem;">{angle.get('title', '')}</h3>
                    <span>{gf_badge}</span>
                </div>
                <p style="color:{COLORS['muted']}; font-size:0.9rem; margin:6px 0 0 0;">{angle.get('description', '')}</p>
            </div>
            """, unsafe_allow_html=True)

    # Benchmarks + Entry Point Papers
    benchmarks = result.get("related_benchmarks", [])
    entry_papers = result.get("entry_point_papers", [])

    if benchmarks or entry_papers:
        st.markdown("---")
        col_b, col_e = st.columns(2)
        with col_b:
            st.subheader("Related Benchmarks")
            if benchmarks:
                for b in benchmarks:
                    st.markdown(f"- {b}")
            else:
                st.caption("None identified.")
        with col_e:
            st.subheader("Entry Point Papers")
            if entry_papers:
                for ep in entry_papers:
                    st.markdown(f"- {ep}")
            else:
                st.caption("None identified.")

    # Save to Project
    if active_project:
        st.markdown("---")
        if st.button("Save to Project", key="save_roadmap", use_container_width=True):
            from src.projects import save_artifact
            save_artifact(active_project, "roadmap", f"Roadmap: {topic[:50]}",
                          {"topic": topic, "constraints": constraints, "result": result},
                          metadata={"topic": topic, "complexity": result.get("complexity", "")})
            st.success("Saved to project!")
