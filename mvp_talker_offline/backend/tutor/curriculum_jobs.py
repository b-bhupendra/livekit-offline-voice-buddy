"""
curriculum_jobs.py — Thin Background Job Dispatch Layer.

The sole dispatch boundary that tool functions in agent.py call directly:
  - enqueue_build: Initial chapter curriculum node generation
  - enqueue_refine: Automated node refinement based on learner error rates
  - enqueue_reconsider: Alternate explanation generation on demand

Gated by GPUSessionArbiter so Tier 2 jobs never trigger model thrashing
during live WebRTC calls on 8GB hardware.
"""

import asyncio
from typing import Optional
from tutor.curriculum_pipeline import pipeline
from core.gpu_arbiter import gpu_arbiter
from core.structured_logger import rag_logger


def enqueue_build(chapter_idx: int, submodule: str, node_id: str) -> asyncio.Task:
    """Enqueue background compilation for a chapter concept node."""
    state = {
        "job_type": "build",
        "node_id": node_id,
        "chapter_idx": chapter_idx,
        "submodule": submodule,
        "attempt": 0,
    }
    config = {"configurable": {"thread_id": f"build:{node_id}"}}

    async def _runner():
        # Await GPU idle before invoking authoring pipeline
        await gpu_arbiter.wait_for_idle()
        rag_logger.info(f"[Job Dispatch] Launching curriculum build for {node_id} ({submodule})")
        return await pipeline.ainvoke(state, config)

    return asyncio.create_task(_runner(), name=f"build_{node_id}")


def enqueue_refine(node_id: str, reason: str) -> asyncio.Task:
    """Enqueue background refinement for a concept with high learner error rates."""
    state = {
        "job_type": "refine",
        "node_id": node_id,
        "refine_reason": reason,
        "attempt": 0,
    }
    config = {"configurable": {"thread_id": f"refine:{node_id}"}}

    async def _runner():
        await gpu_arbiter.wait_for_idle()
        rag_logger.info(f"[Job Dispatch] Launching curriculum refine for {node_id}: {reason}")
        return await pipeline.ainvoke(state, config)

    return asyncio.create_task(_runner(), name=f"refine_{node_id}")


def enqueue_reconsider(node_id: str, style_hint: str, complaint: str, request_id: str) -> asyncio.Task:
    """Enqueue background generation of an alternative explanation variant."""
    state = {
        "job_type": "reconsider",
        "node_id": node_id,
        "style_hint": style_hint,
        "learner_complaint": complaint,
        "attempt": 0,
    }
    config = {"configurable": {"thread_id": f"reconsider:{request_id}"}}

    async def _runner():
        await gpu_arbiter.wait_for_idle()
        rag_logger.info(f"[Job Dispatch] Launching reconsideration for {node_id} (style={style_hint})")
        return await pipeline.ainvoke(state, config)

    return asyncio.create_task(_runner(), name=f"reconsider_{request_id}")
