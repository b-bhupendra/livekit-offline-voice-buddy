"""
curriculum_notify.py — Asynchronous GenUI Broadcast & Context Injection.

Solves the Context Blindness bug (buddy.md Critique #3):
  1. Pushes the rendered canvas payload to the room via WebRTC data channel
  2. Programmatically injects a system message into session.history so the LLM
     knows the card was generated and is currently visible on the learner's screen
  3. Announces the card verbally if Buddy is idle ('listening'), or queues it into
     a pending announcements buffer to be flushed on the next natural pause.
"""

import json
import time
import asyncio
from typing import Dict, Any, Optional, List
from core.structured_logger import genui_logger, tts_logger

_active_session: Any = None
_active_run_context: Any = None
_pending_announcements: List[Dict[str, Any]] = []


def register_active_session(session: Any, run_context: Optional[Any] = None) -> None:
    """Register current LiveKit AgentSession and RunContext for async notifications."""
    global _active_session, _active_run_context
    _active_session = session
    if run_context is not None:
        _active_run_context = run_context


def get_active_session() -> Any:
    return _active_session


def queue_pending_announcement(item: Dict[str, Any]) -> None:
    """Queue announcement to be delivered when Buddy reaches natural speech pause."""
    _pending_announcements.append(item)


def flush_pending_announcements() -> Optional[Dict[str, Any]]:
    """Pop the next pending announcement if available."""
    if _pending_announcements:
        return _pending_announcements.pop(0)
    return None


async def push_ready_event(state: Dict[str, Any]) -> None:
    """
    Broadcast compiled lecture to frontend GenUI and inject context into LLM history.
    """
    draft = state.get("draft") or {}
    node_id = state.get("node_id", "node_default")
    job_type = state.get("job_type", "build")
    title = draft.get("title", state.get("submodule", node_id))
    canvas_type = draft.get("canvas_type", "classifier")
    core_concept = draft.get("core_concept", "")

    req_id = f"req_pipe_{int(time.time() * 1000)}"

    payload = {
        "schema_version": "1.0",
        "type": "genui_render",
        "component": "CanvasLectureCard",
        "props": {
            "id": node_id,
            "req_id": req_id,
            "topic": draft.get("submodule", title),
            "submodule": draft.get("submodule", title),
            "phase_index": state.get("chapter_idx", 1) or 1,
            "session_type": "grammar_mastery",
            "spoken_summary": core_concept,
            "paragraphs": draft.get("lecture_paragraphs", []),
            "canvas_type": canvas_type,
            "canvas_config": draft.get("canvas_config", {}),
            "citations": draft.get("citations", []),
            "timestamp": time.time(),
        }
    }

    # 1. Resolve reconsideration request if applicable
    if job_type == "reconsider":
        try:
            from engines import curriculum_store
            curriculum_store.resolve_reconsideration_request(
                request_id=state.get("node_id", ""),
                resulting_variant_id=state.get("result_id"),
            )
        except Exception as e:
            genui_logger.warning(f"Failed to resolve reconsideration request: {e}")

    # 2. Push GenUI payload over WebRTC data channel
    session = _active_session
    if session and hasattr(session, "room_io") and session.room_io:
        try:
            room = session.room_io.room
            if room and room.local_participant:
                await room.local_participant.publish_data(
                    payload=json.dumps(payload).encode("utf-8"),
                    topic="genui",
                )
                genui_logger.info(f"GenUI card pushed to WebRTC data channel: {title} ({canvas_type})")
        except Exception as err:
            genui_logger.warning(f"WebRTC data channel push notice: {err}")

    # 3. CONTEXT INJECTION (Critique #3 fix)
    # Update LLM's reality so it never hallucinates about what is on screen
    if session and hasattr(session, "history"):
        try:
            system_msg = (
                f"[System: Canvas Lecture '{title}' ({canvas_type}) has been compiled and is now "
                f"rendered on screen for the learner. Core concept: '{core_concept}'. "
                f"You may reference this visual artifact directly in conversation.]"
            )
            session.history.add_message(role="system", content=system_msg)
            genui_logger.info(f"Injected canvas lecture reality into LLM history for {node_id}")
        except Exception as e:
            genui_logger.warning(f"Failed to inject system context into session.history: {e}")

    # 4. Spoken announcement gating
    # If Buddy is idle ('listening'), announce completion; otherwise queue it
    if session:
        agent_state = getattr(session, "agent_state", "listening")
        if agent_state == "listening" and hasattr(session, "generate_reply"):
            try:
                genui_logger.info("Buddy is idle; triggering conversational announcement of ready lecture...")
                asyncio.create_task(session.generate_reply())
            except Exception as e:
                genui_logger.warning(f"Failed to trigger verbal announcement: {e}")
        else:
            queue_pending_announcement({
                "node_id": node_id,
                "title": title,
                "concept": core_concept,
                "timestamp": time.time(),
            })
