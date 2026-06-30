from __future__ import annotations

from pathlib import Path

from backend.app.src.graph.state import AnalysisState
from backend.app.src.graph.workflow import run_analysis


def run_full_analysis_pipeline(state: AnalysisState) -> AnalysisState:
    report = run_analysis(Path(state["pdf_path"]), state["job_id"])
    state["comparison_report"] = report
    return state


def build_optional_langgraph():
    try:
        from langgraph.graph import END, StateGraph
    except ModuleNotFoundError:
        return None
    graph = StateGraph(AnalysisState)
    graph.add_node("run_full_analysis_pipeline", run_full_analysis_pipeline)
    graph.set_entry_point("run_full_analysis_pipeline")
    graph.add_edge("run_full_analysis_pipeline", END)
    return graph.compile()
