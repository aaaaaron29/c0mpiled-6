# ResearchOS - Architecture & Build Log

## Project Overview
ResearchOS is an AI-powered research platform built with Streamlit + LangGraph. It provides 8 tools for research teams: data cleaning, data labeling, review queue, hypothesis validation, contradiction detection, replicability scoring, experiment design critique, and team management.

**Tech Stack:** Streamlit, LangGraph, LangChain, OpenAI (gpt-5-mini), Pydantic V2, PyMuPDF, Pandas
**Run:** `cd researchos && streamlit run app/Home.py`
**Env:** Requires `OPENAI_API_KEY` in `.env` (copy from `.env.example`)

## File Map
| File | Purpose | Status |
|------|---------|--------|
| CLAUDE.md | Architecture doc | in-progress |
| requirements.txt | Dependencies | not started |
| .env.example | Env template | not started |
| README.md | Project readme | not started |
| src/__init__.py | Package init | not started |
| src/config.py | Config + env loading + get_llm() | not started |
| src/models.py | Pydantic V2 schemas (all data models) | not started |
| src/agents.py | LangGraph agent nodes | not started |
| src/graph.py | LangGraph state machine | not started |
| src/prompts.py | Prompt templates | not started |
| src/ingestion.py | CSV/JSON/JSONL data loading | not started |
| src/paper_ingestion.py | PDF paper parsing with PyMuPDF | not started |
| src/llm_utils.py | Shared LLM wrapper + JSON parsing | not started |
| src/export.py | Data export to CSV/JSON/JSONL | not started |
| src/fallback.py | Human review queue | not started |
| src/preprocessors.py | Image preprocessing utilities | not started |
| src/tools/__init__.py | Tools package | not started |
| src/tools/base.py | BaseTool ABC + ToolResult | not started |
| src/tools/cleaning.py | CleaningTool | not started |
| src/tools/labeling.py | LabelingTool | not started |
| src/tools/evaluation.py | EvaluationTool | not started |
| src/tools/pipeline.py | Sequential tool chaining | not started |
| config/rubrics/*.json | 5 evaluation rubrics | not started |
| app/Home.py | Dashboard with 8 tool cards | not started |
| app/theme.py | Design system + CSS + UI helpers | not started |
| app/pages/1_Data_Cleaning.py | Upload, clean, compare, export | not started |
| app/pages/2_Data_Labeling.py | Single + batch labeling with trace | not started |
| app/pages/3_Review_Queue.py | Human review dashboard | not started |
| app/pages/4_Hypothesis_Validator.py | Evaluate hypothesis vs papers | not started |
| app/pages/5_Contradiction_Detector.py | Cross-paper contradiction finder | not started |
| app/pages/6_Replicability_Scorer.py | Methods reproducibility scorer | not started |
| app/pages/7_Design_Critic.py | Experiment design critique | not started |
| app/pages/8_Team_Management.py | Team CRUD + task tracking | not started |

## Architecture
```
User -> Streamlit Pages -> src/ modules -> LLM (OpenAI gpt-5-mini)

Data Pages (1-3):
  Upload -> CleaningTool/LabelingTool -> LangGraph Pipeline -> Results/Export
  Review Queue reads from data/review_queue/ JSON files

Research Pages (4-7):
  Upload PDFs -> paper_ingestion.py (PyMuPDF) -> llm_utils.py -> Structured JSON

Team Page (8):
  Session state CRUD -> No external dependencies

Labeling Pipeline (LangGraph):
  labeler_node -> critic_node -> validator_node | fallback_node
  Retries: critic sends feedback back to labeler up to max_retries
```

## Shared Components
- **paper_ingestion.py**: PDF parsing via PyMuPDF, used by pages 4-7
- **llm_utils.py**: `call_llm()` + `parse_llm_json()`, used by pages 4-7
- **config.py**: `get_config()` + `get_llm()`, used everywhere
- **theme.py**: `page_header()`, `metric_card()`, `badge()`, `conf_bar()`, `trace_step()`

## Config & Environment
- `OPENAI_API_KEY`: Required for LLM features
- Models: gpt-5-mini for labeler, critic, vision
- Temperature: 0.1, Max tokens: 4096, Min confidence: 85, Max retries: 3

## Build Log
- Phase 0: CLAUDE.md created, directory structure scaffolded
- Phase 1: requirements.txt, .env.example, README.md, __init__ files
- Phase 2: Core engine complete — config, models, agents, graph, prompts
- Phase 3: Supporting modules — ingestion, export, fallback, preprocessors, tools/, rubrics/
- Phase 4: Shared research utils — paper_ingestion, llm_utils
- Phase 5: Theme + data pages 1-3 complete
- Phase 6: All research pages 4-7 + Team (8) + Home complete
- BUILD COMPLETE — all imports verified, syntax clean

## Known Issues / TODOs
- LLM features require valid OPENAI_API_KEY in .env
- Data Cleaning works fully offline (no LLM needed)
- Team Management works fully offline (session state only)
- Review Queue works offline (reads JSON files)
- Model: gpt-5-mini used throughout (labeler, critic, vision)
