"""PaperTrail Home Dashboard."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
from app.theme import inject_css, COLORS, render_project_sidebar

st.set_page_config(
    page_title="PaperTrail",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
active_project = render_project_sidebar()

# Hero
st.markdown(f"""
<div style="text-align:center; padding:40px 0 32px 0;">
    <h1 style="font-size:3rem; margin:0;">🔬 PaperTrail</h1>
    <p style="color:{COLORS['muted']}; font-size:1.2rem; margin:12px 0 0 0; max-width:700px; margin-left:auto; margin-right:auto;">
        An AI-powered platform for research teams. From hypothesis to publication —
        discover ideas, analyze literature, build roadmaps, critique designs,
        and process your datasets.
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Tool cards — Research Tools
st.markdown(f"## Research Tools")
st.markdown(f"<p style='color:{COLORS['muted']};'>AI-powered analysis of research papers and hypotheses</p>", unsafe_allow_html=True)

research_tools = [
    {
        "icon": "💡",
        "name": "Idea Engine",
        "desc": "Generate novel research ideas or validate a hypothesis against real papers with AI-powered analysis.",
        "page": "pages/1_Idea_Engine",
        "tags": ["Search", "LLM"],
    },
    {
        "icon": "🗺️",
        "name": "Research Roadmap",
        "desc": "Turn a research interest into an actionable project plan with datasets, methodology, and research angles.",
        "page": "pages/2_Research_Roadmap",
        "tags": ["Search", "LLM"],
    },
    {
        "icon": "🔎",
        "name": "Literature Lens",
        "desc": "Understand the debates, gaps, and open questions in any research area. Surfaces contested claims, emerging directions, and research opportunities.",
        "page": "pages/3_Literature_Lens",
        "tags": ["Search", "Multi-paper", "LLM"],
    },
    {
        "icon": "🧪",
        "name": "Design Critic",
        "desc": "Paste your experimental design — hypothesis, variables, controls, sample size, methodology — and get specific, grounded critique on confounds, missing controls, and methodological concerns.",
        "page": "pages/4_Design_Critic",
        "tags": ["Critique", "LLM"],
    },
]

cols = st.columns(2)
for i, tool in enumerate(research_tools):
    with cols[i % 2]:
        tags_html = " ".join([f'<span style="background:{COLORS["primary"]}20; color:{COLORS["primary"]}; border:1px solid {COLORS["primary"]}40; padding:2px 8px; border-radius:12px; font-size:0.75rem;">{t}</span>' for t in tool["tags"]])
        st.markdown(f"""
        <div class="tool-card">
            <div style="font-size:2rem; margin-bottom:8px;">{tool['icon']}</div>
            <h3 style="margin:0 0 8px 0;">{tool['name']}</h3>
            <p style="color:{COLORS['muted']}; font-size:0.9rem; margin:0 0 12px 0;">{tool['desc']}</p>
            <div>{tags_html}</div>
        </div>
        """, unsafe_allow_html=True)
        st.page_link(f"{tool['page']}.py", label=f"Open {tool['name']} →")

st.divider()

# Data Tools
st.markdown("## Data Tools")
st.markdown(f"<p style='color:{COLORS['muted']};'>Clean, label, and evaluate your research datasets</p>", unsafe_allow_html=True)

data_tools = [
    {
        "icon": "⚙️",
        "name": "Data Processor",
        "desc": "Clean, label, and process your research datasets. PII redaction, dedup, quality scoring, AI labeling with live trace.",
        "page": "pages/5_Data_Processor",
        "tags": ["Offline", "LangGraph", "LLM"],
    },
    {
        "icon": "📋",
        "name": "Review Queue",
        "desc": "Human review dashboard for low-confidence or failed labels. Inspect, manually label, and export.",
        "page": "pages/6_Review_Queue",
        "tags": ["Offline"],
    },
]

cols = st.columns(2)
for i, tool in enumerate(data_tools):
    with cols[i % 2]:
        tags_html = " ".join([f'<span style="background:{COLORS["primary"]}20; color:{COLORS["primary"]}; border:1px solid {COLORS["primary"]}40; padding:2px 8px; border-radius:12px; font-size:0.75rem;">{t}</span>' for t in tool["tags"]])
        st.markdown(f"""
        <div class="tool-card">
            <div style="font-size:2rem; margin-bottom:8px;">{tool['icon']}</div>
            <h3 style="margin:0 0 8px 0;">{tool['name']}</h3>
            <p style="color:{COLORS['muted']}; font-size:0.9rem; margin:0 0 12px 0;">{tool['desc']}</p>
            <div>{tags_html}</div>
        </div>
        """, unsafe_allow_html=True)
        st.page_link(f"{tool['page']}.py", label=f"Open {tool['name']} →")

st.divider()

# Your Projects section
st.markdown("## Your Projects")
from src.projects import get_recent_projects

recent_projects = get_recent_projects(limit=3)
if recent_projects:
    cols = st.columns(min(len(recent_projects), 3))
    for i, proj in enumerate(recent_projects):
        with cols[i]:
            updated = proj["updated_at"][:16].replace("T", " ")
            count = proj.get("artifact_count", 0)
            st.markdown(f"""
            <div class="tool-card">
                <h3 style="margin:0 0 6px 0; font-size:1rem;">{proj['name']}</h3>
                <p style="color:{COLORS['muted']}; font-size:0.85rem; margin:0 0 4px 0;">{proj['description'] or 'No description'}</p>
                <p style="color:{COLORS['muted']}; font-size:0.8rem; margin:0;">{count} artifact{'s' if count != 1 else ''} · Updated {updated}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Load Project", key=f"home_load_{proj['id']}"):
                st.session_state["active_project_id"] = proj["id"]
                st.rerun()
    st.page_link("pages/7_Project_Viewer.py", label="Open Project Viewer →")
else:
    st.caption("No projects yet. Create one using the sidebar.")

st.divider()
st.markdown(f"<p style='text-align:center; color:{COLORS['muted']}; font-size:0.85rem;'>PaperTrail — Built for the AI for Productivity & Research Hackathon</p>", unsafe_allow_html=True)
