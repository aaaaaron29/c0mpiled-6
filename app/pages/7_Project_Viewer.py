"""Project Viewer — See everything saved in your project."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, badge, COLORS, inject_css, render_project_sidebar
from src.projects import get_project, load_artifacts, load_artifact_data, delete_project

st.set_page_config(page_title="Project Viewer — PaperTrail", page_icon="📁", layout="wide")

page_header("Project Viewer", "Browse all artifacts saved to your project.", "📁")
inject_css()
active_project = render_project_sidebar()

ARTIFACT_ICONS = {
    "topic_exploration": "💡",
    "hypothesis_validation": "🔬",
    "roadmap": "🗺️",
    "literature_analysis": "🔎",
    "design_critique": "🧪",
    "cleaned_data": "🧹",
    "labeled_data": "🏷️",
}

ARTIFACT_LABELS = {
    "topic_exploration": "Topic Exploration",
    "hypothesis_validation": "Hypothesis Validation",
    "roadmap": "Research Roadmap",
    "literature_analysis": "Literature Analysis",
    "design_critique": "Design Critique",
    "cleaned_data": "Cleaned Dataset",
    "labeled_data": "Labeled Dataset",
}

if not active_project:
    st.info("Select or create a project using the sidebar to view its contents.")
    st.stop()

project = get_project(active_project)
if not project:
    st.error("Project not found.")
    st.stop()

# Project header
st.markdown(f"""
<div class="tool-card">
    <h2 style="margin:0 0 6px 0;">{project.name}</h2>
    <p style="color:{COLORS['muted']}; margin:0 0 4px 0;">{project.description or 'No description'}</p>
    <p style="color:{COLORS['muted']}; font-size:0.8rem; margin:0;">Created {project.created_at[:16].replace('T', ' ')} · Updated {project.updated_at[:16].replace('T', ' ')}</p>
</div>
""", unsafe_allow_html=True)

artifacts = load_artifacts(active_project)

if not artifacts:
    st.markdown("---")
    st.caption("No artifacts yet. Use the research tools to generate and save results to this project.")
    st.stop()

# Summary metrics
type_counts = {}
for a in artifacts:
    type_counts[a.artifact_type] = type_counts.get(a.artifact_type, 0) + 1

cols = st.columns(min(len(type_counts), 4))
for i, (atype, count) in enumerate(type_counts.items()):
    with cols[i % len(cols)]:
        icon = ARTIFACT_ICONS.get(atype, "📄")
        label = ARTIFACT_LABELS.get(atype, atype.replace("_", " ").title())
        metric_card(f"{icon} {label}", count)

st.markdown("---")

# Timeline view — all artifacts in order
st.subheader(f"Project Timeline ({len(artifacts)} artifacts)")

for idx, artifact in enumerate(reversed(artifacts)):
    icon = ARTIFACT_ICONS.get(artifact.artifact_type, "📄")
    label = ARTIFACT_LABELS.get(artifact.artifact_type, artifact.artifact_type)
    type_badge = badge(label, COLORS["primary"])
    ts = artifact.created_at[:16].replace("T", " ")

    with st.expander(f"{icon} {artifact.name} — {ts}", expanded=(idx == 0)):
        st.markdown(f"{type_badge}", unsafe_allow_html=True)

        data = load_artifact_data(active_project, artifact)
        if data is None:
            st.warning("Artifact data file not found.")
            continue

        # Render based on artifact type
        if artifact.artifact_type == "topic_exploration":
            _render_discovery(data)
        elif artifact.artifact_type == "hypothesis_validation":
            _render_validation(data)
        elif artifact.artifact_type == "roadmap":
            _render_roadmap(data)
        elif artifact.artifact_type == "literature_analysis":
            _render_literature(data)
        elif artifact.artifact_type == "design_critique":
            _render_critique(data)
        elif artifact.artifact_type in ("cleaned_data", "labeled_data"):
            _render_dataframe(data, artifact)
        else:
            st.json(data)

# Delete project (at bottom, guarded)
st.markdown("---")
with st.expander("Danger Zone"):
    st.warning("Deleting a project removes all its artifacts permanently.")
    if st.button("Delete This Project", type="primary"):
        delete_project(active_project)
        st.session_state["active_project_id"] = None
        st.success("Project deleted.")
        st.rerun()


# ---- Render helpers ----

def _render_discovery(data):
    result = data.get("result", {})
    st.markdown(f"**Topic:** {data.get('topic', '')}")
    st.caption(f"{data.get('paper_count', '?')} papers analyzed")

    themes = result.get("themes", [])
    if themes:
        st.markdown("**Themes:**")
        for t in themes:
            st.markdown(f"- {t}")

    gaps = result.get("gaps", [])
    if gaps:
        st.markdown("**Gaps:**")
        for g in gaps:
            st.markdown(f"- {g}")

    ideas = result.get("ideas", [])
    if ideas:
        st.markdown(f"**Ideas ({len(ideas)}):**")
        for idea in ideas:
            f_badge = badge(idea.get("feasibility", "?"), COLORS["primary"])
            st.markdown(f"- **{idea.get('title', '')}** {f_badge} — {idea.get('description', '')}", unsafe_allow_html=True)


def _render_validation(data):
    result = data.get("result", {})
    st.markdown(f"**Hypothesis:** {data.get('hypothesis', '')}")
    verdict = result.get("verdict", "?")
    v_colors = {"Strong": COLORS["success"], "Weak": COLORS["warning"], "Contradicted": COLORS["danger"], "Ungrounded": COLORS["neutral"]}
    v_badge = badge(verdict, v_colors.get(verdict, COLORS["neutral"]))
    st.markdown(f"**Verdict:** {v_badge}", unsafe_allow_html=True)
    if result.get("summary"):
        st.info(result["summary"])
    cols = st.columns(3)
    with cols[0]:
        st.metric("Support", f"{int(result.get('support_score', 0) * 100)}%")
    with cols[1]:
        st.metric("Novelty", f"{int(result.get('novelty_score', 0) * 100)}%")
    with cols[2]:
        st.metric("Feasibility", f"{int(result.get('feasibility_score', 0) * 100)}%")


def _render_roadmap(data):
    result = data.get("result", {})
    st.markdown(f"**Topic:** {data.get('topic', '')}")
    if data.get("constraints"):
        st.caption(f"Constraints: {data['constraints']}")

    complexity = result.get("complexity", "?")
    c_colors = {"Beginner": COLORS["success"], "Intermediate": COLORS["warning"], "Advanced": COLORS["danger"]}
    st.markdown(f"**Complexity:** {badge(complexity, c_colors.get(complexity, COLORS['neutral']))}", unsafe_allow_html=True)

    if result.get("landscape_summary"):
        st.info(result["landscape_summary"])

    steps = result.get("methodology_steps", [])
    if steps:
        st.markdown(f"**Methodology ({len(steps)} steps):**")
        for s in sorted(steps, key=lambda x: x.get("step", 0)):
            st.markdown(f"{s.get('step', '?')}. **{s.get('title', '')}** ({s.get('estimated_time', '')}) — {s.get('description', '')}")

    datasets = result.get("suggested_datasets", [])
    if datasets:
        st.markdown(f"**Datasets ({len(datasets)}):**")
        for ds in datasets:
            st.markdown(f"- **{ds.get('name', '')}** — {ds.get('description', '')}")


def _render_literature(data):
    result = data.get("result", {})
    st.markdown(f"**Topic:** {data.get('topic', '')}")
    st.caption(f"{data.get('paper_count', '?')} papers analyzed")

    intensity = result.get("debate_intensity", "?")
    i_colors = {"Active": COLORS["danger"], "Moderate": COLORS["warning"], "Settled": COLORS["success"]}
    st.markdown(f"**Debate Intensity:** {badge(intensity, i_colors.get(intensity, COLORS['neutral']))}", unsafe_allow_html=True)

    if result.get("field_consensus"):
        st.info(result["field_consensus"])

    contested = result.get("contested_claims", [])
    if contested:
        st.markdown(f"**Contested Claims ({len(contested)}):**")
        for c in contested:
            st.markdown(f"- **{c.get('claim', '')}** — {c.get('why_it_matters', '')}")

    open_qs = result.get("open_questions", [])
    if open_qs:
        st.markdown(f"**Open Questions ({len(open_qs)}):**")
        for q in open_qs:
            st.markdown(f"- {q.get('question', '')} — *{q.get('opportunity', '')}*")


def _render_critique(data):
    result = data.get("result", {})
    st.markdown(f"**Experiment:** {data.get('experiment', '')[:200]}...")

    if result.get("overall_assessment"):
        st.info(result["overall_assessment"])

    all_issues = (result.get("confounds", []) + result.get("missing_controls", []) +
                  result.get("methodological_concerns", []) + result.get("literature_gaps", []))
    critical = len([i for i in all_issues if i.get("severity") == "Critical"])
    major = len([i for i in all_issues if i.get("severity") == "Major"])
    st.markdown(f"**Issues:** {len(all_issues)} total ({critical} critical, {major} major)")

    for issue in all_issues:
        sev = issue.get("severity", "Minor")
        s_colors = {"Critical": COLORS["danger"], "Major": COLORS["warning"], "Minor": COLORS["neutral"]}
        s_badge = badge(sev, s_colors.get(sev, COLORS["neutral"]))
        st.markdown(f"- {s_badge} {issue.get('description', '')}", unsafe_allow_html=True)


def _render_dataframe(data, artifact):
    import pandas as pd
    if isinstance(data, pd.DataFrame):
        st.dataframe(data.head(20), use_container_width=True)
        st.caption(f"{len(data)} rows × {len(data.columns)} columns")
    else:
        st.json(data)
