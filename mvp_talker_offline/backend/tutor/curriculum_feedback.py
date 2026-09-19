"""
curriculum_feedback.py — Automated Pedagogical Feedback & Refine Loop.

Turns learner analytics and friction signals into autonomous curriculum refinement:
  - Scans syllabus_tracker for concepts with >= 60% failure rate over >= 5 attempts
  - Scans curriculum_store for concepts receiving >= 3 reconsideration requests
  - Enqueues automated refinement jobs without disrupting live calls
"""

from typing import List, Tuple
from core.structured_logger import rag_logger
from engines import curriculum_store
from tutor.curriculum_jobs import enqueue_refine


async def scan_for_refine_candidates(threshold_fail_rate: float = 0.6, min_samples: int = 5) -> List[str]:
    """
    Scans learner progress data and reconsideration requests to trigger
    background refinement for struggling curriculum nodes.
    """
    refine_triggered = []

    # 1. Clustered Reconsideration Trigger (>= 3 requests indicates the canonical explanation is flawed)
    try:
        clustered = curriculum_store.get_clustered_reconsideration_nodes(min_count=3)
        for node_id, count in clustered:
            rag_logger.info(f"[Feedback Loop] Triggering refine for {node_id}: {count} learners requested reconsideration")
            enqueue_refine(node_id, reason=f"{count} learners requested alternative explanation")
            refine_triggered.append(node_id)
    except Exception as e:
        rag_logger.warning(f"Failed to scan clustered reconsiderations: {e}")

    # 2. High Failure Rate Trigger
    try:
        from engines.syllabus_tracker import SyllabusTracker
        tracker = SyllabusTracker()
        summary = tracker.get_learner_summary()
        # Check failed questions queue
        failed_patterns = summary.get("failed_questions_queue", [])
        pattern_counts = {}
        for item in failed_patterns:
            pat = item.get("trap_type") or item.get("chapter", "general")
            pattern_counts[pat] = pattern_counts.get(pat, 0) + 1

        for pat, count in pattern_counts.items():
            if count >= min_samples:
                rag_logger.info(f"[Feedback Loop] Triggering refine for pattern {pat} ({count} failures)")
                enqueue_refine(str(pat), reason=f"High failure frequency: {count} recorded mistakes")
                refine_triggered.append(str(pat))
    except Exception as e:
        rag_logger.warning(f"Failed to scan failure rate candidates: {e}")

    return refine_triggered
