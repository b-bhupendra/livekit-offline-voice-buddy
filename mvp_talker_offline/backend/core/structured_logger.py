"""Localized Structured Logging System for LiveKit Voice Agent.
Provides dedicated subsystem loggers with consistent session and turn IDs:
- STT: Faster-Whisper transcription events, audio frames, interim/final latency
- LLM: Generation tokens, inference prompt/completion, latency
- TTS: Audio server synthesis, Piper chunk delivery, playout
- RAG: Hybrid vector + keyword search, embedding availability
- GenUI: Interactive sheets (QuizCard, ContentionResolver, Notes, GrammarMovement, sheet_error)
"""

import os
import sys
import time
import json
import logging
import contextvars
from datetime import datetime
from typing import Any, Dict, Optional

# Context variables for current session and turn tracing
_current_session_id: contextvars.ContextVar[str] = contextvars.ContextVar("session_id", default="session_default")
_current_turn_id: contextvars.ContextVar[int] = contextvars.ContextVar("turn_id", default=0)

def set_session_id(session_id: str) -> None:
    _current_session_id.set(session_id)

def get_session_id() -> str:
    return _current_session_id.get()

def set_turn_id(turn_id: int) -> None:
    _current_turn_id.set(turn_id)

def get_turn_id() -> int:
    return _current_turn_id.get()

def next_turn() -> int:
    new_turn = _current_turn_id.get() + 1
    _current_turn_id.set(new_turn)
    return new_turn

class SubsystemLogAdapter(logging.LoggerAdapter):
    """Logger adapter that injects subsystem name, session_id, and turn_id into every log record."""
    def __init__(self, logger: logging.Logger, subsystem: str):
        super().__init__(logger, {"subsystem": subsystem.upper()})
        self.subsystem = subsystem.upper()

    def process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple:
        extra = kwargs.get("extra", {})
        session_id = extra.get("session_id", get_session_id())
        turn_id = extra.get("turn_id", get_turn_id())
        
        # Build prefix
        prefix = f"[{self.subsystem}] [sess={session_id} turn={turn_id}]"
        
        # If additional structured payload is provided in kwargs
        structured_data = {k: v for k, v in kwargs.items() if k not in ("extra", "exc_info", "stack_info", "stacklevel")}
        if structured_data:
            msg = f"{msg} | {json.dumps(structured_data, default=str)}"
            for k in list(structured_data.keys()):
                kwargs.pop(k)

        formatted_msg = f"{prefix} {msg}"
        return formatted_msg, kwargs

    def event(self, event_name: str, message: str = "", **kwargs):
        """Log a structured domain event at INFO level."""
        data_str = f" | {json.dumps(kwargs, default=str)}" if kwargs else ""
        self.info(f"{event_name}: {message}{data_str}")

# Set up base logger
_base_logger = logging.getLogger("livekit.buddy")
_base_logger.setLevel(logging.INFO)

if not _base_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setLevel(logging.INFO)
    _formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    _handler.setFormatter(_formatter)
    _base_logger.addHandler(_handler)

# Localized logger factories
def get_logger(subsystem: str) -> SubsystemLogAdapter:
    logger = logging.getLogger(f"livekit.buddy.{subsystem.lower()}")
    return SubsystemLogAdapter(logger, subsystem)

# Pre-initialized localized loggers for core voice subsystems
stt_logger = get_logger("STT")
llm_logger = get_logger("LLM")
tts_logger = get_logger("TTS")
rag_logger = get_logger("RAG")
genui_logger = get_logger("GenUI")
system_logger = get_logger("SYSTEM")
