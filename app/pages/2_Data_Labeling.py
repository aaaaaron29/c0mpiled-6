"""Data Labeling page with live agent trace."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import streamlit as st
import pandas as pd
from app.theme import page_header, metric_card, trace_step, conf_bar, inject_css, badge, COLORS
from src.ingestion import load_data, get_text_column
from src.models import LabelingTask
from src.graph import run_labeling_graph
from src.config import get_config
from src.export import get_export_bytes

st.set_page_config(page_title="Data Labeling — ResearchOS", page_icon="🏷️", layout="wide")

page_header("Data Labeling", "AI-powered labeling with critic review and confidence scoring.", "🏷️")

TASK_TYPES = ["sentiment", "ner", "summarization", "object_detection", "ocr", "visual_qa", "captioning", "grounded_description"]

col_cfg1, col_cfg2 = st.columns([2, 1])
with col_cfg1:
    task_type = st.selectbox("Task Type", TASK_TYPES, format_func=lambda x: x.replace("_", " ").title())
with col_cfg2:
    mode = st.radio("Mode", ["Single Item", "Batch"])

if mode == "Single Item":
    st.subheader("Single Item Labeling")
    text_input = st.text_area("Enter text to label", height=150, placeholder="Paste text here...")

    if st.button("Label This Item", type="primary", use_container_width=True):
        if not text_input.strip():
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
                text_content=text_input,
            )

            st.subheader("Agent Trace")
            trace_container = st.container()

            with trace_container:
                with st.spinner("Running labeler..."):
                    # Show trace steps as they conceptually happen
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
                        trace_step("fallback_node", f"Sent to human review", f"Reason: {fallback}", "warning")
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
    # Batch mode
    st.subheader("Batch Labeling")
    uploaded = st.file_uploader("Upload dataset", type=["csv", "json", "jsonl"])

    if uploaded:
        try:
            df = load_data(uploaded)
            st.success(f"Loaded {len(df):,} rows")
            st.dataframe(df.head(5), use_container_width=True)
        except Exception as e:
            st.error(str(e))
            st.stop()

        text_col = get_text_column(df)
        text_col = st.selectbox("Text column", df.columns.tolist(), index=list(df.columns).index(text_col) if text_col in df.columns else 0)
        gt_col_options = ["(none)"] + df.columns.tolist()
        gt_col = st.selectbox("Ground truth column (optional)", gt_col_options)

        max_rows = st.slider("Max rows to label", 1, min(len(df), 50), min(len(df), 10))

        if st.button("Run Batch Labeling", type="primary", use_container_width=True):
            config = get_config()
            if not config.openai_api_key:
                st.error("OPENAI_API_KEY not set.")
                st.stop()

            df_batch = df.head(max_rows).copy()
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
            fallback = len([r for r in results if r.get("fallback_reason")])
            avg_conf = sum(r.get("final_confidence", 0) for r in results) / max(len(results), 1)

            cols = st.columns(4)
            with cols[0]: metric_card("Total Labeled", labeled)
            with cols[1]: metric_card("Avg Confidence", f"{avg_conf:.0f}%")
            with cols[2]: metric_card("Sent to Review", fallback)
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

            fmt = st.selectbox("Export format", ["csv", "json", "jsonl"])
            data_bytes, fname, mime = get_export_bytes(df_batch, fmt)
            st.download_button(f"Download {fmt.upper()}", data=data_bytes, file_name=f"labeled_{fname}", mime=mime, use_container_width=True)
    else:
        inject_css()
        st.info("Upload a dataset file to begin batch labeling.")
