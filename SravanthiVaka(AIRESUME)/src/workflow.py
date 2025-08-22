from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import networkx as nx
import plotly.graph_objects as go

from .agents import AgentResult


@dataclass
class WorkflowTrace:
    steps: List[AgentResult]
    edges: List[Tuple[str, str]]


def build_workflow_trace(steps: List[AgentResult]) -> WorkflowTrace:
    names = [s.name for s in steps]
    edges: List[Tuple[str, str]] = [(names[i], names[i + 1]) for i in range(len(names) - 1)]
    return WorkflowTrace(steps=steps, edges=edges)


def workflow_figure(trace: WorkflowTrace) -> go.Figure:
    g = nx.DiGraph()
    for s in trace.steps:
        g.add_node(s.name)
    for u, v in trace.edges:
        g.add_edge(u, v)

    pos = nx.spring_layout(g, seed=42)

    edge_x, edge_y = [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    # Prepare rich node hover info and conditional coloring
    node_x, node_y, text, hover_texts, colors = [], [], [], [], []
    name_to_step: Dict[str, AgentResult] = {s.name: s for s in trace.steps}
    for n in g.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        text.append(n)
        step = name_to_step.get(n)
        inputs = step.inputs if step else {}
        outputs = step.outputs if step else {}
        reasoning = step.reasoning if step else ""

        def _summarize(d: Dict[str, Any]) -> str:
            items: List[str] = []
            for k, v in list(d.items())[:6]:
                if isinstance(v, (list, tuple)):
                    items.append(f"{k}=[{len(v)}]")
                elif isinstance(v, (int, float)):
                    items.append(f"{k}={v}")
                else:
                    s = str(v)
                    s = s.replace("\n", " ")
                    items.append(f"{k}={s[:40]}{'…' if len(s)>40 else ''}")
            return ", ".join(items)

        hover_text = (
            f"<b>{n}</b><br>"
            f"Inputs: {_summarize(inputs) or '—'}<br>"
            f"Outputs: {_summarize(outputs) or '—'}<br>"
            f"Reasoning: {reasoning[:120]}{'…' if len(reasoning)>120 else ''}"
        )
        hover_texts.append(hover_text)

        # Color code: fallback/orange if reasoning mentions fallback, else blue
        if reasoning and "fallback" in reasoning.lower():
            colors.append("#ff7f0e")  # orange
        else:
            colors.append("#1f77b4")  # blue

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color="#888"), hoverinfo="none", mode="lines")
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=text,
        textposition="bottom center",
        hoverinfo="text",
        hovertext=hover_texts,
        hovertemplate="%{hovertext}<extra></extra>",
        marker=dict(showscale=False, color=colors, size=18, line=dict(width=2, color="#fff")),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), showlegend=False, hovermode="closest")
    return fig
