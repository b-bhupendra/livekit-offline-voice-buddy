"""
gpu_arbiter.py — Application-Level GPU Session Mutex & VRAM Arbiter.

Solves GPU Thrashing on 8GB Hardware (buddy.md Critique #4):
  - On 8GB GPUs, keeping both the 3B conversational model and 7B authoring model
    resident simultaneously causes continuous Ollama VRAM swapping, introducing
    10+ second speech delays and GPU thermal spikes.
  - This arbiter enforces strict voice-call priority:
    When an active WebRTC session is running or the learner is speaking,
    background Tier 2 LangGraph compilation jobs pause at node boundaries.
  - Tier 2 compilation only resumes when the live audio call is idle or disconnected.
"""

import asyncio
from typing import Optional
from core.structured_logger import system_logger


class GPUSessionArbiter:
    """
    Coordinates GPU execution between the live Tier 1 conversational voice loop
    and the asynchronous Tier 2 authoring pipeline.
    """

    def __init__(self):
        self._voice_active: bool = False
        self._idle_event: asyncio.Event = asyncio.Event()
        self._idle_event.set()  # Initially idle / unlocked

    @property
    def is_voice_active(self) -> bool:
        return self._voice_active

    @property
    def is_idle(self) -> bool:
        return not self._voice_active

    def set_voice_active(self, active: bool) -> None:
        """Called by LiveKit session lifecycle and turn events."""
        if self._voice_active != active:
            self._voice_active = active
            if active:
                self._idle_event.clear()
                system_logger.info("[GPU Arbiter] Live voice session ACTIVE -> Tier 2 compilation paused to preserve VRAM.")
            else:
                self._idle_event.set()
                system_logger.info("[GPU Arbiter] Live voice session IDLE -> Tier 2 compilation unlocked.")

    async def wait_for_idle(self, timeout: Optional[float] = None) -> bool:
        """Wait until no active voice session is utilizing the GPU."""
        try:
            if timeout:
                await asyncio.wait_for(self._idle_event.wait(), timeout=timeout)
            else:
                await self._idle_event.wait()
            return True
        except asyncio.TimeoutError:
            return False

    async def tier2_slot(self):
        """Context manager used by Tier 2 tasks to gate LLM execution on voice session inactivity."""
        class _SlotContext:
            def __init__(self, arbiter: GPUSessionArbiter):
                self.arbiter = arbiter

            async def __aenter__(self):
                await self.arbiter.wait_for_idle()
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return _SlotContext(self)


# Global singleton arbiter
gpu_arbiter = GPUSessionArbiter()
