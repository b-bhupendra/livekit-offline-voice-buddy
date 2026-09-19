"""
studio_tts.py — Studio-Quality Pre-rendered Audio Generator for Tier 2.

Synthesizes high-fidelity audio clips for finalized curriculum lectures
and caches them to disk at data/lecture_audio/{node_id}.wav.
Tier 1 conversational turns can play this cached audio with zero synthesis latency.
"""

import os
import io
import wave
import asyncio
from pathlib import Path
from typing import Optional

from core.config import LECTURE_AUDIO_DIR
from core.structured_logger import tts_logger
from core.kokoro_tts import clean_tts_text


async def synthesize_studio_clip(text: str, out_id: str) -> Optional[str]:
    """
    Synthesize high-quality lecture audio and cache as WAV on disk.
    Returns the absolute path to the generated .wav file.
    """
    clean = clean_tts_text(text)
    if not clean:
        return None

    audio_dir = Path(str(LECTURE_AUDIO_DIR))
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_path = audio_dir / f"{out_id}.wav"

    # If already cached, return immediately
    if out_path.exists() and out_path.stat().st_size > 44:
        return str(out_path)

    try:
        from core.kokoro_tts import KokoroTTS
        engine = KokoroTTS()
        pcm_bytes = await engine.synthesize_pcm_async(clean)
        if not pcm_bytes:
            return None

        # Write valid 24kHz 16-bit mono WAV
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm_bytes)

        tts_logger.info(f"Studio audio rendered and cached: {out_path} ({len(pcm_bytes)} bytes)")
        return str(out_path)
    except Exception as e:
        tts_logger.warning(f"Failed to synthesize studio clip for {out_id}: {e}")
        return None
