"""LangGraph tutor graph and curriculum generation."""

try:
    from tutor.langgraph_tutor_graph import langgraph_engine, TutorState
except Exception:
    langgraph_engine = None
    TutorState = None
