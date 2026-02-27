"""Data Cleaning page."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
import pandas as pd
from app.theme import page_header, metric_card, inject_css
from src.ingestion import load_data
from src.tools.cleaning import CleaningTool
from src.export import get_export_bytes

st.set_page_config(page_title="Data Cleaning — ResearchOS", page_icon="🧹", layout="wide")

page_header("Data Cleaning", "Remove PII, deduplicate, and score quality in your dataset.", "🧹")

# Upload
uploaded = st.file_uploader("Upload dataset", type=["csv", "json", "jsonl"])

if uploaded:
    try:
        df_raw = load_data(uploaded)
        st.success(f"Loaded {len(df_raw):,} rows × {len(df_raw.columns)} columns")
    except Exception as e:
        st.error(f"Failed to load file: {e}")
        st.stop()

    st.subheader("Raw Data Preview")
    st.dataframe(df_raw.head(10), use_container_width=True)

    # Options
    st.subheader("Cleaning Options")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        remove_pii = st.checkbox("PII Detection & Masking", value=True)
    with col2:
        dedup = st.checkbox("Deduplication", value=True)
    with col3:
        quality_filter = st.checkbox("Quality Filter (score < 0.3)", value=True)
    with col4:
        outlier_filter = st.checkbox("Outlier Removal (numeric)", value=False)

    if st.button("Run Cleaning", type="primary", use_container_width=True):
        tool = CleaningTool(
            remove_pii=remove_pii,
            dedup=dedup,
            quality_filter=quality_filter,
            outlier_filter=outlier_filter,
        )
        progress = st.progress(0, text="Starting...")

        def update_progress(p, msg):
            progress.progress(p, text=msg)

        with st.spinner("Cleaning in progress..."):
            result = tool.run(df_raw, progress_callback=update_progress)

        progress.empty()

        if result.success:
            st.success("Cleaning complete!")
            m = result.metadata

            # Metrics
            cols = st.columns(4)
            with cols[0]:
                metric_card("Original Rows", f"{m['original_rows']:,}")
            with cols[1]:
                metric_card("Final Rows", f"{m['final_rows']:,}")
            with cols[2]:
                metric_card("PII Found", f"{m['pii_found']:,}", color="#FF4D4D")
            with cols[3]:
                metric_card("Duplicates Removed", f"{m['duplicates_removed']:,}")

            col_a, col_b = st.columns(2)
            with col_a:
                metric_card("Low Quality Removed", f"{m['low_quality_removed']:,}")
            with col_b:
                metric_card("Time", f"{result.elapsed_seconds:.1f}s")

            # Before/after comparison
            st.subheader("Before / After Comparison")
            tab1, tab2 = st.tabs(["Before", "After"])
            with tab1:
                st.dataframe(df_raw.head(20), use_container_width=True)
            with tab2:
                st.dataframe(result.data.head(20), use_container_width=True)

            # Export
            st.subheader("Export")
            fmt = st.selectbox("Format", ["csv", "json", "jsonl"])
            data_bytes, fname, mime = get_export_bytes(result.data, fmt)
            st.download_button(f"Download {fmt.upper()}", data=data_bytes, file_name=fname, mime=mime, use_container_width=True)
        else:
            for err in result.errors:
                st.error(err)
else:
    inject_css()
    st.info("Upload a CSV, JSON, or JSONL file to get started.")
