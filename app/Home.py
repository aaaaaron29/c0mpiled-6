"""ResearchOS Home Dashboard."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
from app.theme import inject_css, COLORS

st.set_page_config(
    page_title="ResearchOS",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# Hero
st.markdown(f"""
<div style="text-align:center; padding:40px 0 32px 0;">
    <h1 style="font-size:3rem; margin:0;">🔬 ResearchOS</h1>
    <p style="color:{COLORS['muted']}; font-size:1.2rem; margin:12px 0 0 0; max-width:700px; margin-left:auto; margin-right:auto;">
        An AI-powered platform for research teams. From hypothesis to publication —
        validate ideas, detect contradictions, score methods, critique designs,
        clean data, label datasets, and manage your team.
    </p>
</div>
""", unsafe_allow_html=True)

st.divider()

# Tool cards — Research Tools
st.markdown(f"## Research Tools")
st.markdown(f"<p style='color:{COLORS['muted']};'>AI-powered analysis of research papers and hypotheses</p>", unsafe_allow_html=True)

research_tools = [
    {
        "icon": "🔬",
        "name": "Hypothesis Validator",
        "desc": "Evaluate your hypothesis against uploaded papers. Get support score, novelty score, feasibility score, and cited evidence.",
        "page": "pages/4_Hypothesis_Validator",
        "tags": ["PDF", "LLM"],
    },
    {
        "icon": "⚡",
        "name": "Contradiction Detector",
        "desc": "Upload 5–15 papers and find conflicting claims across them. Ranked by severity: Direct, Partial, Contextual.",
        "page": "pages/5_Contradiction_Detector",
        "tags": ["PDF", "Multi-paper"],
    },
    {
        "icon": "📊",
        "name": "Replicability Scorer",
        "desc": "Score a paper's methods section for reproducibility across 6 criteria. Identify critical gaps and get improvement suggestions.",
        "page": "pages/6_Replicability_Scorer",
        "tags": ["PDF", "Scoring"],
    },
    {
        "icon": "🧪",
        "name": "Design Critic",
        "desc": "Describe your experiment and get specific, grounded critique: confounds, missing controls, methodological concerns.",
        "page": "pages/7_Design_Critic",
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
        "icon": "🧹",
        "name": "Data Cleaning",
        "desc": "Remove PII, deduplicate, score quality, and detect outliers in CSV/JSON/JSONL datasets.",
        "page": "pages/1_Data_Cleaning",
        "tags": ["Offline", "CSV", "JSON"],
    },
    {
        "icon": "🏷️",
        "name": "Data Labeling",
        "desc": "AI labeling pipeline with LangGraph: labeler → critic → validator. Live trace, batch mode, confidence scores.",
        "page": "pages/2_Data_Labeling",
        "tags": ["LangGraph", "LLM"],
    },
    {
        "icon": "📋",
        "name": "Review Queue",
        "desc": "Human review dashboard for low-confidence or failed labels. Inspect, manually label, and export.",
        "page": "pages/3_Review_Queue",
        "tags": ["Offline"],
    },
]

cols = st.columns(3)
for i, tool in enumerate(data_tools):
    with cols[i]:
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

# Team Management
st.markdown("## Team")
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"""
    <div class="tool-card">
        <div style="font-size:2rem; margin-bottom:8px;">👥</div>
        <h3 style="margin:0 0 8px 0;">Team Management</h3>
        <p style="color:{COLORS['muted']}; font-size:0.9rem; margin:0;">
            Add team members, assign roles (PI, Postdoc, PhD, etc.), create tasks linked to specific modules,
            and track progress across your research team.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/8_Team_Management.py", label="Open Team Management →")

st.divider()
st.markdown(f"<p style='text-align:center; color:{COLORS['muted']}; font-size:0.85rem;'>ResearchOS — Built for the AI for Productivity & Research Hackathon</p>", unsafe_allow_html=True)
