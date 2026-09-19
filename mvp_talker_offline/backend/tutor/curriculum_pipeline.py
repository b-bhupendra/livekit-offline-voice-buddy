"""
curriculum_pipeline.py — Shared 8-Node LangGraph Curriculum Compiler.

Implements the single shared authoring pipeline for:
  - build: Initial chapter concept compilation from textbook & course RAG chunks
  - refine: Updating nodes with high learner failure rates
  - reconsider: Generating alternate pedagogical analogies on demand

States:
  retrieve_context -> draft_content -> deterministic_gate -> semantic_critic
  -> (persist -> render_audio -> notify) OR (retry draft_content) OR (flag_and_stop -> notify)
"""

import os
import sqlite3
from typing import TypedDict, Literal, Optional, List, Dict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from core.config import CHECKPOINT_DB_PATH
from core.structured_logger import rag_logger, genui_logger
from engines.rag_store import RAGStore
from engines import curriculum_store
from tutor.curriculum_authoring import (
    CurriculumNode,
    CriticVerdict,
    structured_authoring_call,
    critic_call,
)


class PipelineState(TypedDict):
    job_type: Literal["build", "refine", "reconsider"]
    node_id: str
    chapter_idx: Optional[int]
    submodule: Optional[str]
    style_hint: Optional[str]         # for reconsider
    learner_complaint: Optional[str]  # for reconsider
    refine_reason: Optional[str]      # for refine
    retrieved_chunks: List[Dict[str, Any]]
    draft: Optional[Dict[str, Any]]
    gate_passed: bool
    critic_passed: bool
    critic_feedback: Optional[str]
    attempt: int
    result_id: Optional[str]


async def retrieve_context(state: PipelineState) -> Dict[str, Any]:
    """Retrieve grounded textbook and lecture chunks from ChromaDB."""
    rag = RAGStore()
    submodule = state.get("submodule") or state.get("node_id", "Grammar")
    job_type = state.get("job_type", "build")

    if job_type == "reconsider":
        query = f"{submodule} {state.get('style_hint', '')} {state.get('learner_complaint', '')}"
    elif job_type == "refine":
        query = f"{submodule} rules exceptions traps {state.get('refine_reason', '')}"
    else:
        query = f"{submodule} rules exceptions examples grammar patterns"

    chunks = rag.hybrid_search(query, top_k=5)
    rag_logger.info(f"Pipeline [{job_type}:{state['node_id']}] retrieved {len(chunks)} chunks for query: '{query}'")
    return {"retrieved_chunks": chunks}


async def draft_content(state: PipelineState) -> Dict[str, Any]:
    """Synthesize structured CurriculumNode matching schema with feedback integration."""
    submodule = state.get("submodule") or state.get("node_id", "Grammar")
    node_id = state.get("node_id", "node_default")
    chapter_idx = state.get("chapter_idx", 1) or 1
    job_type = state.get("job_type", "build")
    style_hint = state.get("style_hint", "everyday")

    chunk_context = "\n---\n".join([
        f"Source: {c.get('source_title', 'Grammar Reference')} | Section: {c.get('section_title', '')}\n{c.get('text', '')}"
        for c in state.get("retrieved_chunks", [])
    ])

    prompt = (
        f"Create an educational curriculum node for topic '{submodule}' (Chapter {chapter_idx}).\n"
        f"Job Type: {job_type}. Target Analogy Style: {style_hint}.\n\n"
        f"Grounded Source Context:\n{chunk_context or 'Use standard grammatical guidelines.'}\n\n"
        f"Instructions:\n"
        f"1. node_id: '{node_id}'\n"
        f"2. title: Clear pedagogical title for '{submodule}'\n"
        f"3. core_concept: Single clear sentence stating the rule or contrast\n"
        f"4. lecture_paragraphs: 2-3 engaging, grounded educational paragraphs\n"
        f"5. canvas_type: select the best matching primitive from ['classifier', 'matrix', 'tree', 'flow']\n"
        f"6. canvas_config: json object suitable for rendering the canvas_type\n"
        f"7. citations: list exact titles of sources from the context that directly support the lesson\n"
    )

    attempt = state.get("attempt", 0) + 1
    draft_node = await structured_authoring_call(
        CurriculumNode,
        prompt=prompt,
        feedback=state.get("critic_feedback"),
        max_retries=3,
    )

    rag_logger.info(f"Pipeline [{job_type}:{node_id}] generated draft attempt {attempt}: '{draft_node.title}' ({draft_node.canvas_type})")
    return {
        "draft": draft_node.model_dump(),
        "attempt": attempt,
    }


async def deterministic_gate(state: PipelineState) -> Dict[str, Any]:
    """
    Deterministic citation audit:
    Verifies that cited sources are present in the retrieved chunks or standard curriculum.
    """
    draft = state.get("draft") or {}
    citations = draft.get("citations") or []
    retrieved = state.get("retrieved_chunks") or []
    chunk_sources = " ".join([c.get("source_title", "") + " " + c.get("text", "") for c in retrieved]).lower()

    # Pass if no citations required or citations appear in retrieved chunks / standard sources
    passed = True
    if citations and retrieved:
        # Check if at least 1 citation matches source chunks
        match_count = sum(1 for cite in citations if cite.lower() in chunk_sources or "oxford" in cite.lower() or "arihant" in cite.lower() or "udemy" in cite.lower())
        passed = (match_count > 0)

    curriculum_store.log_critique(
        node_id=state["node_id"],
        job_type=state["job_type"],
        stage="deterministic_gate",
        passed=passed,
        detail=None if passed else "Uncited or hallucinated source claims in draft",
        attempt_number=state.get("attempt", 1),
    )

    rag_logger.info(f"Deterministic gate for [{state['node_id']}]: passed={passed}")
    return {"gate_passed": passed}


async def semantic_critic(state: PipelineState) -> Dict[str, Any]:
    """Invokes distinct auditor model to critique semantic clarity and pedagogical rigor."""
    # If deterministic gate failed, skip semantic critic to save compute
    if not state.get("gate_passed", True):
        return {"critic_passed": False, "critic_feedback": "Deterministic gate failed: source citations not grounded."}

    draft = state.get("draft") or {}
    critic_prompt = (
        f"Topic: {draft.get('title', '')}\n"
        f"Core Concept: {draft.get('core_concept', '')}\n"
        f"Paragraphs: {json.dumps(draft.get('lecture_paragraphs', []))}\n"
        f"Canvas Type: {draft.get('canvas_type', '')}\n\n"
        f"Does this draft provide clear, linguistically correct English instruction "
        f"suitable for an interactive ESL voice buddy? Answer with passed=true/false and feedback."
    )

    verdict = await critic_call(critic_prompt)
    curriculum_store.log_critique(
        node_id=state["node_id"],
        job_type=state["job_type"],
        stage="semantic_critic",
        passed=verdict.passed,
        detail=verdict.feedback,
        attempt_number=state.get("attempt", 1),
    )

    rag_logger.info(f"Semantic critic for [{state['node_id']}]: passed={verdict.passed}")
    return {
        "critic_passed": verdict.passed,
        "critic_feedback": verdict.feedback,
    }


def route_after_critic(state: PipelineState) -> str:
    """Decide whether to persist, retry drafting with critic feedback, or flag and stop."""
    if state.get("gate_passed", False) and state.get("critic_passed", False):
        return "persist"
    if state.get("attempt", 0) >= 3:
        return "flag_and_stop"
    return "draft_content"


async def persist(state: PipelineState) -> Dict[str, Any]:
    """Save finalized node or variant into data/curriculum.db."""
    job_type = state.get("job_type", "build")
    node_id = state["node_id"]
    draft = state["draft"] or {}

    if job_type in ("build", "refine"):
        result_id = curriculum_store.save_node(
            node_id=node_id,
            draft=draft,
            chapter_idx=state.get("chapter_idx", 1) or 1,
            submodule=state.get("submodule", node_id),
        )
    else:  # reconsider
        result_id = curriculum_store.save_variant(
            node_id=node_id,
            style=state.get("style_hint", "everyday"),
            draft=draft,
        )

    rag_logger.info(f"Pipeline successfully persisted {job_type} -> result_id: {result_id}")
    return {"result_id": result_id}


async def render_audio(state: PipelineState) -> Dict[str, Any]:
    """Synthesize studio-quality pre-rendered audio for the finalized lecture paragraphs."""
    try:
        from tutor.studio_tts import synthesize_studio_clip
        draft = state.get("draft") or {}
        paras = draft.get("lecture_paragraphs") or []
        full_text = " ".join(paras)
        result_id = state.get("result_id", state["node_id"])

        audio_path = await synthesize_studio_clip(full_text, out_id=result_id)
        if audio_path:
            curriculum_store.attach_audio(state["job_type"], result_id, audio_path)
    except Exception as e:
        rag_logger.warning(f"Audio pre-render failed (non-fatal): {e}")

    return {}


async def notify(state: PipelineState) -> Dict[str, Any]:
    """Push GenUI over WebRTC data channel and inject context into live agent session."""
    try:
        from tutor.curriculum_notify import push_ready_event
        await push_ready_event(state)
    except Exception as e:
        rag_logger.warning(f"Pipeline notification failed: {e}")

    return {}


async def flag_and_stop(state: PipelineState) -> Dict[str, Any]:
    """Flag node for human review after 3 failed attempts."""
    curriculum_store.flag_node(
        node_id=state["node_id"],
        job_type=state["job_type"],
        reason=state.get("critic_feedback", "Retries exhausted without passing critic"),
    )
    return {}


def build_pipeline(checkpointer: Any) -> Any:
    """Build and compile the 8-node LangGraph authoring StateGraph."""
    builder = StateGraph(PipelineState)

    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("draft_content", draft_content)
    builder.add_node("deterministic_gate", deterministic_gate)
    builder.add_node("semantic_critic", semantic_critic)
    builder.add_node("persist", persist)
    builder.add_node("render_audio", render_audio)
    builder.add_node("notify", notify)
    builder.add_node("flag_and_stop", flag_and_stop)

    builder.add_edge(START, "retrieve_context")
    builder.add_edge("retrieve_context", "draft_content")
    builder.add_edge("draft_content", "deterministic_gate")
    builder.add_edge("deterministic_gate", "semantic_critic")

    builder.add_conditional_edges(
        "semantic_critic",
        route_after_critic,
        {
            "persist": "persist",
            "draft_content": "draft_content",
            "flag_and_stop": "flag_and_stop",
        }
    )

    builder.add_edge("persist", "render_audio")
    builder.add_edge("render_audio", "notify")
    builder.add_edge("notify", END)
    builder.add_edge("flag_and_stop", "notify")

    return builder.compile(checkpointer=checkpointer)


# ─────────────────────────────────────────────────────────────────────────────
# Compiled Pipeline Singleton
# ─────────────────────────────────────────────────────────────────────────────

_checkpoint_conn = sqlite3.connect(str(CHECKPOINT_DB_PATH), check_same_thread=False)
_checkpointer = SqliteSaver(_checkpoint_conn)
_checkpointer.setup()
pipeline = build_pipeline(_checkpointer)
