# UI Components (`src/ui_components.py`)

Tiny helpers for displaying results.

- `show_workflow_diagram(fig)`: draws the workflow figure
- `show_agent_outputs(outputs)`: expandable list of agent outputs as JSON
- `show_match_summary(score, confidence, missing_skills, explanation, top_snippets)`: shows metrics and highlights

These keep `app.py` clean and readable.
