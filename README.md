# ResearchOS

An AI-powered platform for research teams. From hypothesis to publication, validate ideas, check contradictions, score methods, critique designs, clean data, label datasets, and manage your team.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
streamlit run app/Home.py
```

## Tools

1. **Data Cleaning** — PII detection, deduplication, quality scoring
2. **Data Labeling** — LangGraph pipeline with critic + retry loop
3. **Review Queue** — Human review for low-confidence labels
4. **Hypothesis Validator** — Evaluate hypotheses against uploaded papers
5. **Contradiction Detector** — Find contradictions across paper sets
6. **Replicability Scorer** — Score methods sections for reproducibility
7. **Design Critic** — Critique experiment designs before running them
8. **Team Management** — Members, roles, and task tracking
