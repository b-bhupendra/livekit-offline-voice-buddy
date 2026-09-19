"""
kokoro_tts.py — Native LiveKit Streaming TTS Plugin for Kokoro-82M ONNX.

Implements LiveKit Agents' official tts.TTS and tts.SynthesizeStream interfaces:
  - Sub-300ms Time-To-First-Audio (TTFA) via clause-boundary streaming
  - Emits raw 24kHz int16 PCM bytes directly to tts.AudioEmitter
  - Eliminates the HTTP round-trip, WAV header overhead, and sentence-buffering latency
  - Fallback to Piper ONNX or silence buffer if Kokoro model files are unavailable
"""

import os
import re
import asyncio
import time
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np

from livekit.agents import tts, utils
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from core.config import (
    KOKORO_MODEL_PATH,
    KOKORO_VOICES_PATH,
    KOKORO_VOICE,
    KOKORO_SPEED,
    PIPER_VOICE_PATH,
    PIPER_LENGTH_SCALE,
    PIPER_NOISE_SCALE,
    PIPER_NOISE_W_SCALE,
)
from core.structured_logger import tts_logger

CLAUSE_BOUNDARY_REGEX = re.compile(r'([,.;:!?\n]+)')


def clean_tts_text(text: str) -> str:
    """Strip emoji, non-ASCII decoration, and normalize whitespace for TTS."""
    cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    cleaned = re.sub(r'[^\w\s.,!?;:\'\"-]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


class KokoroSynthesizeStream(tts.SynthesizeStream):
    """
    LiveKit SynthesizeStream subclass that consumes LLM tokens and synthesizes
    audio on clause boundaries (commas, periods, question marks) for sub-300ms TTFA.
    """

    def __init__(self, *, tts_instance: "KokoroTTS", conn_options: APIConnectOptions):
        super().__init__(tts=tts_instance, conn_options=conn_options)
        self._tts_instance: "KokoroTTS" = tts_instance

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=self._tts_instance.sample_rate,
            num_channels=self._tts_instance.num_channels,
            mime_type="audio/pcm",
            stream=True,
        )

        buffer = ""
        current_segment_id: Optional[str] = None

        async def _synthesize_and_push(text_to_speak: str):
            nonlocal current_segment_id
            clean = clean_tts_text(text_to_speak)
            if not clean:
                return

            pcm_bytes = await self._tts_instance.synthesize_pcm_async(clean)
            if not pcm_bytes:
                return

            if not current_segment_id:
                current_segment_id = utils.shortuuid()
                output_emitter.start_segment(segment_id=current_segment_id)

            output_emitter.push(pcm_bytes)
            output_emitter.flush()

        try:
            async for data in self._input_ch:
                if isinstance(data, str):
                    buffer += data
                    # Check for clause boundaries
                    parts = CLAUSE_BOUNDARY_REGEX.split(buffer)
                    # If we have at least 1 boundary (parts has at least: [before, boundary, after])
                    if len(parts) >= 3:
                        # Extract the first chunk (text + boundary)
                        chunk_text = parts[0] + parts[1]
                        words = chunk_text.strip().split()
                        # Emit if word count is >= 3 or ends with terminal punctuation (. ? ! \n)
                        is_terminal = any(parts[1].endswith(p) for p in [".", "?", "!", "\n"])
                        if len(words) >= 3 or is_terminal:
                            buffer = "".join(parts[2:])
                            await _synthesize_and_push(chunk_text)

                elif isinstance(data, tts.SynthesizeStream._FlushSentinel):
                    if buffer.strip():
                        await _synthesize_and_push(buffer.strip())
                        buffer = ""

                    if current_segment_id:
                        output_emitter.end_segment()
                        current_segment_id = None

            # End of input channel
            if buffer.strip():
                await _synthesize_and_push(buffer.strip())
                buffer = ""

            if current_segment_id:
                output_emitter.end_segment()
                current_segment_id = None

        except Exception as e:
            tts_logger.error(f"Error in KokoroSynthesizeStream._run: {e}")
            raise


class KokoroChunkedStream(tts.ChunkedStream):
    """Fallback non-streaming chunked stream."""

    def __init__(self, *, tts_instance: "KokoroTTS", input_text: str, conn_options: APIConnectOptions):
        super().__init__(tts=tts_instance, input_text=input_text, conn_options=conn_options)
        self._tts_instance: "KokoroTTS" = tts_instance

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=self._tts_instance.sample_rate,
            num_channels=self._tts_instance.num_channels,
            mime_type="audio/pcm",
            stream=False,
        )
        clean = clean_tts_text(self._input_text)
        if clean:
            pcm_bytes = await self._tts_instance.synthesize_pcm_async(clean)
            if pcm_bytes:
                output_emitter.push(pcm_bytes)
                output_emitter.flush()


class KokoroTTS(tts.TTS):
    """
    Native LiveKit Agents TTS plugin running Kokoro-82M ONNX in-process.
    Provides clause-boundary streaming without any external HTTP microservice hop.
    """

    def __init__(
        self,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        model_path: Optional[str] = None,
        voices_path: Optional[str] = None,
        sample_rate: int = 24000,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._voice = voice or KOKORO_VOICE
        self._speed = speed if speed is not None else KOKORO_SPEED
        self._model_path = model_path or str(KOKORO_MODEL_PATH)
        self._voices_path = voices_path or str(KOKORO_VOICES_PATH)
        self._kokoro = None
        self._piper = None

        self._init_engine()

    def _init_engine(self) -> None:
        """Initialize Kokoro-82M ONNX or fallback to Piper ONNX."""
        try:
            from kokoro_onnx import Kokoro as KokoroOnnx
            if os.path.exists(self._model_path) and os.path.exists(self._voices_path):
                self._kokoro = KokoroOnnx(self._model_path, self._voices_path)
                tts_logger.info(
                    f"KokoroTTS native plugin ready | voice={self._voice} | "
                    f"speed={self._speed} | rate={self.sample_rate}Hz [100% in-process]"
                )
                return
            else:
                tts_logger.warning(
                    f"Kokoro model files missing ({self._model_path}). Checking Piper fallback..."
                )
        except Exception as e:
            tts_logger.warning(f"Failed to load Kokoro ONNX: {e}")

        # Piper fallback
        piper_path = str(PIPER_VOICE_PATH)
        if os.path.exists(piper_path):
            try:
                from piper import PiperVoice
                self._piper = PiperVoice.load(piper_path)
                tts_logger.info(f"Piper TTS loaded as fallback | voice={piper_path}")
            except Exception as e:
                tts_logger.warning(f"Failed to load Piper fallback: {e}")

    def synthesize_pcm(self, text: str) -> bytes:
        """Synchronously synthesize text to int16 PCM bytes."""
        if not text:
            return b""

        # Tier 1: Kokoro ONNX
        if self._kokoro is not None:
            try:
                samples, sr = self._kokoro.create(
                    text,
                    voice=self._voice,
                    speed=self._speed,
                    lang="en-us",
                )
                # Convert float32 [-1.0, 1.0] to int16 PCM bytes
                int16_samples = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
                return int16_samples.tobytes()
            except Exception as e:
                tts_logger.warning(f"Kokoro synthesis failed for '{text[:40]}...': {e}")

        # Tier 2: Piper ONNX fallback
        if self._piper is not None:
            try:
                import io, wave
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    self._piper.synthesize(text, wf)
                # Read raw PCM from WAV buffer
                buf.seek(0)
                with wave.open(buf, "rb") as wf:
                    return wf.readframes(wf.getnframes())
            except Exception as e:
                tts_logger.warning(f"Piper synthesis fallback failed: {e}")

        # Tier 3: Silence fallback (100ms) to prevent audio pipeline crash
        silence_samples = int(self.sample_rate * 0.1)
        return np.zeros(silence_samples, dtype=np.int16).tobytes()

    async def synthesize_pcm_async(self, text: str) -> bytes:
        """Asynchronously synthesize text on a worker thread to avoid blocking asyncio loop."""
        return await asyncio.to_thread(self.synthesize_pcm, text)

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> tts.ChunkedStream:
        return KokoroChunkedStream(tts_instance=self, input_text=text, conn_options=conn_options)

    def stream(
        self, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> tts.SynthesizeStream:
        return KokoroSynthesizeStream(tts_instance=self, conn_options=conn_options)
