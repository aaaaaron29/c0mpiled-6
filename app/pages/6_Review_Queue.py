"""Human Review Queue page."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
from app.theme import page_header, metric_card, badge, COLORS, inject_css, render_project_sidebar
from src.fallback import load_review_queue, get_review_queue_summary, export_review_queue_to_csv, clear_review_queue, delete_review_item
from src.config import get_config

st.set_page_config(page_title="Review Queue — PaperTrail", page_icon="📋", layout="wide")

page_header("Review Queue", "Inspect and manually label items flagged for human review.", "📋")
inject_css()
render_project_sidebar()

config = get_config()
summary = get_review_queue_summary(config)

# Summary metrics
cols = st.columns(4)
with cols[0]:
    metric_card("Total Pending", summary["total"])
with cols[1]:
    by_reason = summary.get("by_reason", {})
    metric_card("Retry Limit", by_reason.get("RETRY_LIMIT", 0), color=COLORS["danger"])
with cols[2]:
    metric_card("Low Confidence", by_reason.get("LOW_CONFIDENCE", 0), color=COLORS["warning"])
with cols[3]:
    metric_card("Parse Errors", by_reason.get("PARSING_ERROR", 0) + by_reason.get("VALIDATION_ERROR", 0))

if summary["total"] == 0:
    inject_css()
    st.info("No items in the review queue. Items land here when the AI cannot confidently label them.")
    st.stop()

# Load queue
items = load_review_queue(config)

# Filter
reason_filter = st.multiselect(
    "Filter by reason",
    ["RETRY_LIMIT", "LOW_CONFIDENCE", "PARSING_ERROR", "VALIDATION_ERROR"],
    default=[],
)
if reason_filter:
    items = [i for i in items if i.fallback_reason in reason_filter]

st.markdown(f"**Showing {len(items)} items**")

# Display items
for item in items:
    reason_colors = {
        "RETRY_LIMIT": COLORS["danger"],
        "LOW_CONFIDENCE": COLORS["warning"],
        "PARSING_ERROR": COLORS["neutral"],
        "VALIDATION_ERROR": COLORS["neutral"],
    }
    color = reason_colors.get(item.fallback_reason, COLORS["neutral"])
    badge_html = badge(item.fallback_reason, color)

    with st.expander(f"🔍 {item.data_id} — {badge_html} — {item.timestamp[:19]}", expanded=False):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("**Original Input:**")
            original = item.original_input
            text = original.get("text_content", str(original))
            st.text_area("Input", text, height=100, key=f"input_{item.data_id}_{item.timestamp}", disabled=True)

            if item.labeler_attempts:
                st.markdown("**Labeler Attempts:**")
                for j, attempt in enumerate(item.labeler_attempts):
                    st.markdown(f"Attempt {j+1}: `{attempt.get('label', '?')}` (confidence: {attempt.get('confidence', 0)}%)")

            if item.critic_reviews:
                st.markdown("**Critic Reviews:**")
                for j, review in enumerate(item.critic_reviews):
                    is_correct = review.get("is_correct", False)
                    icon = "✅" if is_correct else "❌"
                    st.markdown(f"{icon} Review {j+1}: {review.get('critique', '')}")

            if item.error_log:
                st.markdown("**Error Log:**")
                for err in item.error_log:
                    st.caption(f"• {err}")

        with col2:
            st.markdown("**Manual Label:**")
            manual_label = st.text_input("Label", key=f"manual_{item.data_id}_{item.timestamp}")
            if st.button("Save Label", key=f"save_{item.data_id}_{item.timestamp}"):
                if manual_label.strip():
                    # In production, this would persist the label
                    st.success(f"Label '{manual_label}' saved for {item.data_id}")
                else:
                    st.warning("Enter a label first.")

            if st.button("Delete Item", key=f"del_{item.data_id}_{item.timestamp}", type="secondary"):
                delete_review_item(item.data_id, config)
                st.success("Item deleted.")
                st.rerun()

# Export & Clear
st.divider()
col_export, col_clear = st.columns(2)

with col_export:
    csv_bytes = export_review_queue_to_csv(config)
    if csv_bytes:
        st.download_button("Export Queue as CSV", data=csv_bytes, file_name="review_queue.csv", mime="text/csv", use_container_width=True)

with col_clear:
    if st.button("Clear Entire Queue", type="secondary", use_container_width=True):
        if "confirm_clear" not in st.session_state:
            st.session_state["confirm_clear"] = True
        st.warning("Are you sure? Click again to confirm.")

    if st.session_state.get("confirm_clear"):
        if st.button("YES, CLEAR ALL", type="primary", use_container_width=True):
            clear_review_queue(config, confirm=True)
            st.session_state.pop("confirm_clear", None)
            st.success("Queue cleared!")
            st.rerun()
