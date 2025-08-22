# Workflow (`src/workflow.py`)

Draws a simple diagram of the agent steps and their order.

## How it works

- `build_workflow_trace(steps)`: stores the list of agent results and edges between consecutive steps
- `workflow_figure(trace)`: makes a Plotly graph:
  - nodes = agent names
  - edges = step order
  - layout = spring layout (auto positions)

The app then shows this figure with `st.plotly_chart`.
