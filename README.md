# PaperTrail

An AI-powered research platform built for the **AI for Productivity & Research Hackathon**. From idea to publication — generate research ideas, analyze literature, build project roadmaps, critique experiment designs, and process your datasets.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
streamlit run app/Home.py
```

## Tools

### Research Tools
| Tool | What it does |
|------|-------------|
| **Idea Engine** | Generate novel research ideas from paper analysis, or validate a hypothesis against real literature with support/novelty/feasibility scores |
| **Research Roadmap** | Enter a topic and get an actionable project plan — auto-searches papers, then generates methodology steps, datasets, prerequisites, and research angles |
| **Literature Lens** | Multi-paper analysis that surfaces field consensus, contested claims (Side A vs Side B), open questions, methodological inconsistencies, and emerging directions |
| **Design Critic** | Paste your experimental design and get specific, grounded critique — confounds, missing controls, methodological concerns, and literature gaps, each rated by severity |

### Data Tools
| Tool | What it does |
|------|-------------|
| **Data Processor** | Clean and label research datasets — PII redaction, deduplication, quality scoring, and AI labeling powered by a LangGraph pipeline with critic/retry loop and live trace |
| **Review Queue** | Human review dashboard for low-confidence or failed labels — inspect, manually label, and export |

### Project System
| Tool | What it does |
|------|-------------|
| **Project Sidebar** | Create and switch between projects from any page — artifacts are saved per-project with a single click |
| **Project Viewer** | Browse all artifacts saved to a project in a timeline view with custom renderers for each artifact type |

## How it works

```
Research pages:
  Search (Semantic Scholar / OpenAlex) or Upload PDFs
  → Paper ingestion (PyMuPDF)
  → LLM analysis (OpenAI gpt-5-mini)
  → Structured results
  → Save to project (SQLite)

Data pages:
  Upload CSV/JSON → Cleaning tools → LangGraph labeling pipeline → Export

Cross-page navigation:
  Idea Engine → "Build Roadmap" auto-runs Research Roadmap
  Literature Lens → "Explore in Idea Engine" prefills Idea Engine
```

## Tech Stack

- **Frontend:** Streamlit (multipage app)
- **LLM:** OpenAI gpt-5-mini
- **Agents:** LangGraph (labeling pipeline: labeler → critic → validator/fallback)
- **Paper Search:** Semantic Scholar + OpenAlex (automatic fallback)
- **PDF Parsing:** PyMuPDF (fitz)
- **Storage:** SQLite (projects + artifacts), filesystem (artifact data files)
- **Data:** Pandas, Pydantic V2

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | Powers all LLM features |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Increases paper search rate limit |
| `OPENALEX_EMAIL` | No | Enables OpenAlex polite pool access |
