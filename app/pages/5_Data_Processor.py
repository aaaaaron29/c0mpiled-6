"""Data Processor — Clean and label your research datasets."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
import pandas as pd
from app.theme import page_header, metric_card, trace_step, conf_bar, inject_css, badge, COLORS, render_project_sidebar
from src.ingestion import load_data, get_text_column
from src.tools.cleaning import CleaningTool
from src.models import LabelingTask
from src.graph import run_labeling_graph
from src.config import get_config
from src.export import get_export_bytes

st.set_page_config(page_title="Data Processor — PaperTrail", page_icon="⚙️", layout="wide")

page_header("Data Processor", "Clean and label your research datasets.", "⚙️")
inject_css()

active_project = render_project_sidebar()

# ---- Shared file upload ----
uploaded_file = st.file_uploader("Upload your dataset", type=["csv", "json", "jsonl"])
df_raw = None

if uploaded_file:
    try:
        df_raw = load_data(uploaded_file)
        st.success(f"Loaded {len(df_raw):,} rows × {len(df_raw.columns)} columns")
        with st.expander("Data Preview", expanded=False):
            st.dataframe(df_raw.head(20), use_container_width=True)
    except Exception as e:
        st.error(f"Failed to load file: {e}")

# ---- Tabs ----
tab_clean, tab_label = st.tabs(["🧹 Clean", "🏷️ Label"])

# ============================================================
# CLEAN TAB — ported from 1_Data_Cleaning.py
# ============================================================
with tab_clean:
    if df_raw is not None:
        st.subheader("Cleaning Options")
        col1, col2 = st.columns(2)
        with col1:
            handle_missing = st.checkbox("Handle missing values", value=True, key="clean_missing")
            normalize_cols = st.checkbox("Normalize column names", value=True, key="clean_normalize")
            remove_pii = st.checkbox("Detect & redact PII", value=True, key="clean_pii")
        with col2:
            dedup = st.checkbox("Remove duplicates", value=True, key="clean_dedup")
            quality_filter = st.checkbox("Quality scoring", value=True, key="clean_quality")
            outlier_filter = st.checkbox("Outlier detection", value=False, key="clean_outlier")

        if st.button("Run Cleaning Pipeline", type="primary", use_container_width=True, key="run_clean"):
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
                    metric_card("Cleaned Rows", f"{m['final_rows']:,}")
                with cols[2]:
                    metric_card("PII Detections", f"{m['pii_found']:,}", color=COLORS["danger"])
                with cols[3]:
                    metric_card("Duplicates Removed", f"{m['duplicates_removed']:,}")

                # Badges showing which steps ran
                steps_run = []
                if handle_missing:
                    steps_run.append("Missing Values")
                if normalize_cols:
                    steps_run.append("Normalize Cols")
                if remove_pii:
                    steps_run.append("PII Redaction")
                if dedup:
                    steps_run.append("Dedup")
                if quality_filter:
                    steps_run.append("Quality Filter")
                if outlier_filter:
                    steps_run.append("Outlier Detection")
                badges_html = " ".join([badge(s, COLORS["primary"]) for s in steps_run])
                st.markdown(badges_html, unsafe_allow_html=True)

                # Before/after comparison
                st.subheader("Before / After Comparison")
                tab_before, tab_after = st.tabs(["Before", "After"])
                with tab_before:
                    st.dataframe(df_raw.head(20), use_container_width=True)
                with tab_after:
                    st.dataframe(result.data.head(20), use_container_width=True)

                # Export
                st.subheader("Export")
                fmt = st.selectbox("Format", ["csv", "json", "jsonl"], key="clean_export_fmt")
                data_bytes, fname, mime = get_export_bytes(result.data, fmt)
                st.download_button(f"Download {fmt.upper()}", data=data_bytes, file_name=fname, mime=mime, use_container_width=True, key="clean_download")

                # Save to Project
                if active_project:
                    st.markdown("---")
                    save_name = st.text_input("Artifact name", value="Cleaned dataset", key="clean_save_name")
                    if st.button("Save to Project", key="clean_save_proj", use_container_width=True):
                        from src.projects import save_dataframe_artifact
                        save_dataframe_artifact(
                            active_project, "cleaned_data", save_name, result.data,
                            metadata={"original_rows": m["original_rows"], "final_rows": m["final_rows"]},
                        )
                        st.success(f"Saved '{save_name}' to project!")

                # Store for label tab reuse
                st.session_state["_cleaned_df"] = result.data
            else:
                for err in result.errors:
                    st.error(err)
    else:
        st.info("Upload a CSV, JSON, or JSONL file above to clean your data.")

# ============================================================
# LABEL TAB — ported from 2_Data_Labeling.py
# ============================================================
with tab_label:
    TASK_TYPES = ["sentiment", "ner", "summarization", "object_detection", "ocr", "visual_qa", "captioning", "grounded_description"]
    VISION_TASKS = ["object_detection", "ocr", "visual_qa", "captioning", "grounded_description"]

    input_mode = st.radio("Input mode", ["From uploaded file", "Upload images"], horizontal=True, key="label_input_mode")

    if input_mode == "From uploaded file":
        # Filter to all task types
        task_type = st.selectbox("Task Type", TASK_TYPES, format_func=lambda x: x.replace("_", " ").title(), key="label_task_type")
        label_mode = st.radio("Mode", ["Single Item (with trace)", "Batch"], horizontal=True, key="label_mode")

        if label_mode == "Single Item (with trace)":
            # ---- Single Item ----
            if df_raw is not None:
                text_col = get_text_column(df_raw)
                col_options = df_raw.columns.tolist()
                text_col = st.selectbox("Text column", col_options, index=col_options.index(text_col) if text_col in col_options else 0, key="single_text_col")
                row_idx = st.number_input("Row index", min_value=0, max_value=max(0, len(df_raw) - 1), value=0, key="single_row_idx")
                text_content = str(df_raw.iloc[row_idx][text_col])
                st.text_area("Text preview", text_content, height=120, disabled=True, key="single_preview")
            else:
                text_content = st.text_area("Enter text to label", height=150, placeholder="Paste text here...", key="single_text_input")

            if st.button("Label This Item", type="primary", use_container_width=True, key="run_single_label"):
                if not text_content.strip():
                    st.warning("Please enter some text.")
                else:
                    config = get_config()
                    if not config.openai_api_key:
                        st.error("OPENAI_API_KEY not set. Add it to your .env file.")
                        st.stop()

                    task = LabelingTask(
                        data_id="single_001",
                        modality="TEXT",
                        task_type=task_type,
                        text_content=text_content,
                    )

                    st.subheader("Agent Trace")
                    trace_container = st.container()

                    with trace_container:
                        with st.spinner("Running labeler..."):
                            trace_step("labeler_node", "Running...", f"Task: {task_type}", "")

                        result = run_labeling_graph(task, config)

                        if result.get("label") == "ERROR":
                            trace_step("labeler_node", "Failed", result.get("reasoning", ""), "error")
                            st.error(f"Labeling failed: {result.get('reasoning')}")
                        else:
                            trace_step("labeler_node", f"Label: {result.get('label')}", f"Confidence: {result.get('confidence', 0)}%", "success")
                            trace_step("critic_node", "Review complete", f"Critic confidence: {result.get('critic_confidence', 0)}%", "success")

                            fallback = result.get("fallback_reason")
                            if fallback:
                                trace_step("fallback_node", "Could not be confidently labeled", f"Reason: {fallback}", "warning")
                            else:
                                trace_step("validator_node", "Validated", f"Final confidence: {result.get('final_confidence', 0)}%", "success")

                    # Result display
                    st.subheader("Result")
                    cols = st.columns(3)
                    with cols[0]:
                        metric_card("Label", result.get("label", "—"))
                    with cols[1]:
                        metric_card("Final Confidence", f"{result.get('final_confidence', 0)}%")
                    with cols[2]:
                        metric_card("Retries", str(result.get("retry_count", 0)))

                    conf_bar(result.get("final_confidence", 0), "Confidence")

                    if result.get("reasoning"):
                        st.markdown("**Reasoning:**")
                        st.info(result["reasoning"])

        else:
            # ---- Batch Mode ----
            if df_raw is not None:
                text_col = get_text_column(df_raw)
                col_options = df_raw.columns.tolist()
                text_col = st.selectbox("Text column", col_options, index=col_options.index(text_col) if text_col in col_options else 0, key="batch_text_col")
                gt_col_options = ["(none)"] + df_raw.columns.tolist()
                gt_col = st.selectbox("Ground truth column (optional)", gt_col_options, key="batch_gt_col")
                max_rows = st.slider("Max rows to label", 1, min(len(df_raw), 50), min(len(df_raw), 10), key="batch_max_rows")

                if st.button("Run Batch Labeling", type="primary", use_container_width=True, key="run_batch_label"):
                    config = get_config()
                    if not config.openai_api_key:
                        st.error("OPENAI_API_KEY not set.")
                        st.stop()

                    df_batch = df_raw.head(max_rows).copy()
                    results = []
                    progress = st.progress(0, text="Starting...")

                    for i, (idx, row) in enumerate(df_batch.iterrows()):
                        text = str(row.get(text_col, ""))
                        task = LabelingTask(
                            data_id=str(idx),
                            modality="TEXT",
                            task_type=task_type,
                            text_content=text,
                        )
                        try:
                            r = run_labeling_graph(task, config)
                        except Exception as e:
                            r = {"data_id": str(idx), "label": "ERROR", "confidence": 0, "final_confidence": 0, "retry_count": 0, "reasoning": str(e)}
                        results.append(r)
                        progress.progress((i + 1) / max_rows, f"Labeled {i+1}/{max_rows}...")

                    progress.empty()
                    st.success("Batch complete!")

                    results_df = pd.DataFrame(results)
                    df_batch = df_batch.reset_index(drop=True)
                    for col in ["label", "confidence", "final_confidence", "retry_count", "reasoning"]:
                        if col in results_df.columns:
                            df_batch[col] = results_df[col].values

                    # Metrics
                    labeled = len([r for r in results if r.get("label") != "ERROR"])
                    fallback_count = len([r for r in results if r.get("fallback_reason")])
                    avg_conf = sum(r.get("final_confidence", 0) for r in results) / max(len(results), 1)

                    cols = st.columns(4)
                    with cols[0]: metric_card("Total Labeled", labeled)
                    with cols[1]: metric_card("Avg Confidence", f"{avg_conf:.0f}%")
                    with cols[2]: metric_card("Fallbacks", fallback_count)
                    with cols[3]: metric_card("Errors", len(results) - labeled)

                    # Evaluation if ground truth available
                    if gt_col != "(none)" and gt_col in df_batch.columns:
                        st.subheader("Evaluation")
                        from src.tools.evaluation import EvaluationTool
                        eval_tool = EvaluationTool(pred_col="label", gt_col=gt_col)
                        eval_result = eval_tool.run(df_batch)
                        if eval_result.success:
                            m = eval_result.metadata
                            ecols = st.columns(3)
                            with ecols[0]: metric_card("Accuracy", f"{m['accuracy']*100:.1f}%")
                            with ecols[1]: metric_card("Macro F1", f"{m['macro_f1']*100:.1f}%")
                            with ecols[2]: metric_card("ECE", f"{m.get('ece', 0)*100:.2f}%" if m.get('ece') is not None else "N/A")

                    st.subheader("Results")
                    st.dataframe(df_batch, use_container_width=True)

                    fmt = st.selectbox("Export format", ["csv", "json", "jsonl"], key="batch_export_fmt")
                    data_bytes, fname, mime = get_export_bytes(df_batch, fmt)
                    st.download_button(f"Download {fmt.upper()}", data=data_bytes, file_name=f"labeled_{fname}", mime=mime, use_container_width=True, key="batch_download")

                    # Save to Project
                    if active_project:
                        st.markdown("---")
                        save_name = st.text_input("Artifact name", value="Labeled dataset", key="label_save_name")
                        if st.button("Save to Project", key="label_save_proj", use_container_width=True):
                            from src.projects import save_dataframe_artifact
                            save_dataframe_artifact(
                                active_project, "labeled_data", save_name, df_batch,
                                metadata={"rows": len(df_batch), "task_type": task_type},
                            )
                            st.success(f"Saved '{save_name}' to project!")
            else:
                st.info("Upload a dataset file above to begin batch labeling.")

    else:
        # ---- Image Mode ----
        task_type = st.selectbox("Task Type", VISION_TASKS, format_func=lambda x: x.replace("_", " ").title(), key="img_task_type")
        uploaded_images = st.file_uploader("Upload images", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="img_upload")
        text_prompt = st.text_input("Optional text prompt", placeholder="e.g. What objects are in this image?", key="img_prompt")

        if uploaded_images and st.button("Label Images", type="primary", use_container_width=True, key="run_img_label"):
            config = get_config()
            if not config.openai_api_key:
                st.error("OPENAI_API_KEY not set.")
                st.stop()

            import base64
            results = []
            for img_file in uploaded_images:
                img_bytes = img_file.read()
                b64 = base64.b64encode(img_bytes).decode()
                task = LabelingTask(
                    data_id=img_file.name,
                    modality="IMAGE",
                    task_type=task_type,
                    text_content=text_prompt or f"Perform {task_type} on this image.",
                    image_path=f"data:image/png;base64,{b64}",
                )
                try:
                    r = run_labeling_graph(task, config)
                except Exception as e:
                    r = {"data_id": img_file.name, "label": "ERROR", "confidence": 0, "final_confidence": 0, "retry_count": 0, "reasoning": str(e)}
                results.append((img_file, img_bytes, r))

            for img_file, img_bytes, r in results:
                col_img, col_res = st.columns([1, 2])
                with col_img:
                    st.image(img_bytes, caption=img_file.name, width=200)
                with col_res:
                    st.markdown(f"**Label:** {r.get('label', '—')}")
                    st.markdown(f"**Confidence:** {r.get('final_confidence', 0)}%")
                    if r.get("reasoning"):
                        st.caption(r["reasoning"])
                st.markdown("---")
