# PaperTrail - Architecture & Build Log

## Project Overview
PaperTrail is an AI-powered research platform built with Streamlit + LangGraph for the AI for Productivity & Research Hackathon. It provides 6 tools for research teams: idea generation, research roadmaps, literature analysis, experiment design critique, data processing, and human review.

**Tech Stack:** Streamlit, LangGraph, LangChain, OpenAI (gpt-5-mini), Pydantic V2, PyMuPDF, Pandas, SQLite
**Run:** `cd papertrail && streamlit run app/Home.py`
**Env:** Requires `OPENAI_API_KEY` in `.env` (copy from `.env.example`)
**Repo:** https://github.com/aaaaaron29/c0mpiled-6

## File Map
| File | Purpose |
|------|---------|
| CLAUDE.md | Architecture doc |
| requirements.txt | Dependencies |
| .env.example | Env template |
| .env | API keys (gitignored) |
| .gitignore | Ignores .env, data/, __pycache__ |
| src/__init__.py | Package init |
| src/config.py | Config + env loading + get_llm() — singleton, gpt-5-mini defaults |
| src/models.py | Pydantic V2 schemas (all data models) |
| src/projects.py | Project CRUD + artifact storage — SQLite backend |
| src/agents.py | LangGraph agent nodes (fallback import wrapped in try/except) |
| src/graph.py | LangGraph state machine |
| src/prompts.py | Prompt templates |
| src/ingestion.py | CSV/JSON/JSONL data loading |
| src/paper_ingestion.py | PDF paper parsing with PyMuPDF |
| src/llm_utils.py | Shared LLM wrapper + JSON parsing |
| src/export.py | Data export to CSV/JSON/JSONL |
| src/fallback.py | Human review queue |
| src/preprocessors.py | Image preprocessing utilities |
| src/paper_search.py | Semantic Scholar + OpenAlex paper search with fallback |
| src/search_widget.py | Reusable Streamlit search+select UI for papers |
| src/tools/base.py | BaseTool ABC + ToolResult |
| src/tools/cleaning.py | CleaningTool |
| src/tools/labeling.py | LabelingTool |
| src/tools/evaluation.py | EvaluationTool |
| src/tools/pipeline.py | Sequential tool chaining |
| config/rubrics/*.json | 5 evaluation rubrics |
| app/Home.py | Dashboard — research tools, data tools, recent projects |
| app/theme.py | Design system + CSS + UI helpers + render_project_sidebar() |
| app/pages/1_Idea_Engine.py | Research Discovery + Hypothesis Validation (2 modes) |
| app/pages/2_Research_Roadmap.py | Auto paper search → methodology, datasets, angles |
| app/pages/3_Literature_Lens.py | Multi-paper analysis: debates, gaps, open questions |
| app/pages/4_Design_Critic.py | Experiment critique: confounds, controls, methods |
| app/pages/5_Data_Processor.py | Clean + Label tabs — PII, dedup, AI labeling with LangGraph trace |
| app/pages/6_Review_Queue.py | Human review dashboard for low-confidence labels |
| app/pages/7_Project_Viewer.py | Browse all artifacts saved to a project |

## Architecture
```
User -> Streamlit Pages -> src/ modules -> LLM (OpenAI gpt-5-mini)

Research Pages (1-4):
  [Search tab]  paper_search.py (Semantic Scholar / OpenAlex) -> search_widget.py
             -> search_results_to_papers() -> same paper dict format
  [Upload tab]  Upload PDFs -> paper_ingestion.py (PyMuPDF)
  Both paths -> llm_utils.py -> Structured JSON -> Save to Project (SQLite)

Data Pages (5-6):
  Upload -> CleaningTool/LabelingTool -> LangGraph Pipeline -> Results/Export
  Review Queue reads from data/review_queue/ JSON files

Project System (SQLite):
  src/projects.py — DB at data/papertrail.db
  Tables: projects (id, name, description, timestamps)
          artifacts (id, project_id FK CASCADE, type, name, filename, metadata_json)
  Artifact files stored in data/projects/<project_id>/
  Sidebar: render_project_sidebar() in theme.py — create, select, view artifacts

Labeling Pipeline (LangGraph):
  labeler_node -> critic_node -> validator_node | fallback_node
  Retries: critic sends feedback back to labeler up to max_retries

Cross-page navigation:
  Idea Engine "Build Roadmap" -> Research Roadmap (auto-executes via roadmap_topic)
  Literature Lens "Explore in Idea Engine" -> Idea Engine (prefills via idea_engine_topic)
```

## Shared Components
- **projects.py**: SQLite project CRUD + artifact storage, absolute paths via _ROOT
- **paper_ingestion.py**: PDF parsing via PyMuPDF, used by pages 1-4
- **llm_utils.py**: `call_llm()` + `parse_llm_json()`, used by pages 1-4
- **config.py**: `get_config()` + `get_llm()`, singleton pattern, loads .env on import
- **theme.py**: `page_header()`, `metric_card()`, `badge()`, `conf_bar()`, `trace_step()`, `severity_badge()`, `verdict_badge()`, `render_project_sidebar()`
- **search_widget.py**: `render_search_widget()` + `search_results_to_papers()`

## Project System
- **Backend**: SQLite at `data/papertrail.db` (gitignored)
- **DB init**: `init_db()` called on module import (CREATE TABLE IF NOT EXISTS)
- **Paths**: `_ROOT` resolved via `os.path.abspath(__file__)` — all paths absolute
- **Artifact types**: topic_exploration, hypothesis_validation, roadmap, literature_analysis, design_critique, cleaned_data, labeled_data
- **Sidebar**: Every page calls `render_project_sidebar()` — create/select projects, view artifact count
- **Save**: Each research page has "Save to Project" button (only shown when project is active)
- **Viewer**: Project Viewer (page 7) renders each artifact type with custom display

## Config & Environment
- `OPENAI_API_KEY`: Required for LLM features
- `SEMANTIC_SCHOLAR_API_KEY`: Optional — increases Semantic Scholar rate limit
- `OPENALEX_EMAIL`: Optional — enables OpenAlex polite pool access
- Models: gpt-5-mini for all LLM calls
- Temperature: 0.1, Max tokens: 4096, Min confidence: 85, Max retries: 3

## Build Log
- Phase 0: CLAUDE.md, directory structure
- Phase 1: requirements.txt, .env.example, README.md
- Phase 2: Core engine — config, models, agents, graph, prompts
- Phase 3: Supporting modules — ingestion, export, fallback, preprocessors, tools/, rubrics/
- Phase 4: Shared research utils — paper_ingestion, llm_utils
- Phase 5: Theme + data pages complete
- Phase 6: All research pages + Home complete
- Phase 7: paper_search.py + search_widget.py — tabbed search/upload input on all research pages
- Phase 8: Renamed Hypothesis Validator → Idea Engine (Discovery + Validation modes)
- Phase 9: Added Research Roadmap page with auto paper search
- Phase 10: Renamed Contradiction Detector → Literature Lens (debates, gaps, open questions)
- Phase 11: Project system — src/projects.py (JSON backend), sidebar, save buttons, Project Viewer
- Phase 12: Removed Replicability Scorer and Team Management pages
- Phase 13: Migrated project system to SQLite backend, normalized paths
- Phase 14: Renumbered pages (1-7) to match Home layout, auto-execute roadmap, updated descriptions
