"""Design system + reusable UI helpers."""
import streamlit as st

# Color palette
COLORS = {
    "primary": "#6C63FF",
    "success": "#00C48C",
    "warning": "#FFB800",
    "danger": "#FF4D4D",
    "neutral": "#8A8A9A",
    "bg": "#0E1117",
    "card": "#1A1D27",
    "border": "#2A2D3E",
    "text": "#FAFAFA",
    "muted": "#8A8A9A",
}

SEVERITY_COLORS = {
    "Critical": COLORS["danger"],
    "Major": COLORS["warning"],
    "Minor": COLORS["neutral"],
    "Direct": COLORS["danger"],
    "Partial": COLORS["warning"],
    "Contextual": COLORS["neutral"],
}

VERDICT_COLORS = {
    "Strong": COLORS["success"],
    "Weak": COLORS["warning"],
    "Contradicted": COLORS["danger"],
    "Ungrounded": COLORS["neutral"],
}


def inject_css():
    st.markdown(f"""
    <style>
    .stApp {{ background-color: {COLORS['bg']}; }}
    .metric-card {{
        background: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 20px;
        margin: 8px 0;
    }}
    .tool-card {{
        background: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 24px;
        margin: 12px 0;
        transition: border-color 0.2s;
    }}
    .tool-card:hover {{ border-color: {COLORS['primary']}; }}
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}
    .trace-step {{
        background: {COLORS['card']};
        border-left: 3px solid {COLORS['primary']};
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 6px 0;
        font-family: monospace;
        font-size: 0.85rem;
    }}
    .trace-step.success {{ border-left-color: {COLORS['success']}; }}
    .trace-step.warning {{ border-left-color: {COLORS['warning']}; }}
    .trace-step.error {{ border-left-color: {COLORS['danger']}; }}
    .conf-bar-bg {{
        background: {COLORS['border']};
        border-radius: 4px;
        height: 8px;
        overflow: hidden;
    }}
    .conf-bar-fill {{
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s;
    }}
    h1, h2, h3 {{ color: {COLORS['text']} !important; }}
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = ""):
    inject_css()
    st.markdown(f"""
    <div style="padding: 8px 0 24px 0; border-bottom: 1px solid {COLORS['border']}; margin-bottom: 24px;">
        <h1 style="margin:0; font-size:2rem;">{icon} {title}</h1>
        {f'<p style="color:{COLORS["muted"]}; margin:6px 0 0 0;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def metric_card(label: str, value, delta=None, color: str = None):
    color = color or COLORS["primary"]
    delta_html = ""
    if delta is not None:
        delta_color = COLORS["success"] if str(delta).startswith("+") else COLORS["danger"]
        delta_html = f'<span style="color:{delta_color}; font-size:0.85rem;">{delta}</span>'
    st.markdown(f"""
    <div class="metric-card">
        <div style="color:{COLORS['muted']}; font-size:0.8rem; text-transform:uppercase; letter-spacing:1px;">{label}</div>
        <div style="color:{color}; font-size:2rem; font-weight:700; margin:4px 0;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def card(content_html: str):
    st.markdown(f'<div class="tool-card">{content_html}</div>', unsafe_allow_html=True)


def badge(text: str, color: str = None):
    color = color or COLORS["primary"]
    text_color = "#FFFFFF"
    return f'<span class="badge" style="background:{color}20; color:{color}; border:1px solid {color}40;">{text}</span>'


def conf_bar(value: int, label: str = ""):
    """Render a confidence bar (value 0-100)."""
    if value >= 85:
        color = COLORS["success"]
    elif value >= 60:
        color = COLORS["warning"]
    else:
        color = COLORS["danger"]

    st.markdown(f"""
    <div style="margin:4px 0;">
        {f'<span style="font-size:0.8rem; color:{COLORS["muted"]};">{label}</span>' if label else ''}
        <div class="conf-bar-bg">
            <div class="conf-bar-fill" style="width:{value}%; background:{color};"></div>
        </div>
        <span style="font-size:0.75rem; color:{color};">{value}%</span>
    </div>
    """, unsafe_allow_html=True)


def trace_step(node: str, status: str, detail: str = "", step_type: str = ""):
    """Render a pipeline trace step."""
    icons = {"labeler": "🏷️", "critic": "🔍", "validator": "✅", "fallback": "⚠️"}
    icon = icons.get(node.lower().split("_")[0], "⚙️")
    css_class = {"success": "success", "warning": "warning", "error": "error"}.get(step_type, "")
    st.markdown(f"""
    <div class="trace-step {css_class}">
        <strong>{icon} {node}</strong>
        {f'<span style="color:{COLORS["muted"]}; margin-left:8px;">{status}</span>' if status else ''}
        {f'<div style="margin-top:4px; color:{COLORS["muted"]}; font-size:0.8rem;">{detail}</div>' if detail else ''}
    </div>
    """, unsafe_allow_html=True)


def severity_badge(severity: str) -> str:
    color = SEVERITY_COLORS.get(severity, COLORS["neutral"])
    return badge(severity, color)


def verdict_badge(verdict: str) -> str:
    color = VERDICT_COLORS.get(verdict, COLORS["neutral"])
    return badge(verdict, color)
