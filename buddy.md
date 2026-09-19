This is a highly rigorous, well-researched implementation plan. Adopting LangGraph’s `AsyncSqliteSaver` for durable job execution, utilizing LiveKit’s native `tts.TTS` plugin for raw PCM audio, and leaning on `ChatOllama.with_structured_output` for deterministic curriculum generation are all architecturally correct decisions that solve the fundamental issues of the previous prototype.

However, a critical review reveals a few missing pedagogical pieces, a misunderstanding of how LiveKit TTS streaming actually behaves under the hood, and a dangerous context-blindness bug in the async tool execution.

Here is a critique of the flaws in the plan, followed by concrete improvements.

### 1. The Missing Fatal Flaw: Whisper Normalization (Pedagogical Failure)

**The Flaw:** Section 1 details 8 "Confirmed root causes" to fix first, but it completely drops the most critical blocker identified in previous reviews: **Whisper auto-corrects ESL grammar mistakes**. If a learner says, *"Yesterday I go to market,"* Faster-Whisper's language model naturally fixes this to *"Yesterday I went to the market."*
**Why it matters:** If Tier 1's goal is to be a co-learner that catches slips, and Tier 2 generates isomorphic questions based on failure rates, the entire system collapses if the STT engine hides the errors from the LLM.
**The Fix:** Add a 9th root cause to Section 1. You must override the `FasterWhisperSTT` initialization to include `condition_on_previous_text=False` and provide a strict `initial_prompt` (e.g., *"Transcribe verbatim with exact grammatical errors"*).

### 2. TTS Plugin Latency: `ChunkedStream` vs. `SynthesizeStream`

**The Flaw:** In Section 2.2, the plan proposes subclassing `tts.TTS` and overriding `synthesize()` to return a `KokoroChunkedStream`, inside of which you run `split_sentences(self.input_text)`.
**Why it fails to achieve sub-500ms latency:** In LiveKit Agents, if a plugin does not implement the dynamic `stream()` method (returning a `SynthesizeStream`), the framework falls back to a wrapper (`StreamedFromChunkedStream`). This wrapper *buffers the incoming LLM tokens until it detects a full sentence boundary* before it even calls your `synthesize()` method.
If the framework already splits the text into sentences, running `split_sentences` again inside your `ChunkedStream` is redundant. Worse, waiting for the LLM to finish an entire sentence before passing it to Kokoro adds 300–600ms of unnecessary delay.
**The Fix:** Do not just override `synthesize()`. Override the `stream()` method and return a subclass of `tts.SynthesizeStream`.

* Implement `push_text(token)` to buffer tokens locally.
* The millisecond a clause boundary (`,`, `.`, `?`) is detected in the stream, pass that short text chunk to Kokoro and push the resulting bytes to `AudioEmitter`. This achieves true token-to-audio streaming.

### 3. Context Blindness After Async Tool Execution (§2.3)

**The Flaw:** Section 2.3 describes latency masking: the tool returns immediately with a bridge line (*"Let me pull that up"*), kicks off a background LangGraph job, and then pushes a GenUI JSON payload to the room via WebRTC once the job finishes.
**Why it breaks the agent:** By returning immediately, the LLM finishes its turn and stops thinking. When the background job finishes 30 seconds later and pushes the UI card to the screen, **the LLM has no idea the card was generated**. If the user looks at the screen and says, *"Buddy, what does this diagram mean?"*, Buddy will hallucinate because the UI generation event is completely absent from its `ChatContext`.
**The Fix:** Pushing to the WebRTC data channel is only half the job. When the LangGraph job finishes, you must programmatically inject an invisible system message into the conversation history and trigger a new inference pass:

```python
# Upon background task completion:
await send_room_text(context, "genui", payload)
# Update the LLM's reality:
session.chat_ctx.append(ChatMessage(role="system", content=f"[System: Canvas Lecture {node_id} rendered on screen.]"))
# Optionally make Buddy announce it:
await session.agent.generate_reply() 

```

### 4. GPU Thrashing on 8GB Hardware (§6.1)

**The Flaw:** Section 6.1 correctly identifies VRAM contention between the 3B live model and the 7B authoring model. It suggests setting `OLLAMA_KEEP_ALIVE` short enough so the authoring model unloads from memory during live calls.
**The Hardware Reality:** Ollama model unloading/loading takes several seconds. If a background job is running the 7B model and the user suddenly speaks, LiveKit requests the 3B model. Ollama will flush the 7B model from VRAM, load the 3B model, serve the audio turn, and then immediately flush the 3B model to reload the 7B model to resume the background job. This causes massive "model thrashing," resulting in 10+ second conversational delays and GPU temperature spikes.
**The Fix:** You cannot rely on passive VRAM eviction. You must implement an explicit **Application-Level Mutex Lock**. If an `AgentSession` (live voice call) becomes active, you must programmatically *pause* the Tier 2 LangGraph checkpointer job queue entirely. Tier 2 compilation can only safely execute when no WebRTC audio session is connected.

### 5. `langgraph dev` Persistence Workaround (§6.3)

**The Flaw:** The plan notes that `langgraph dev` ignores `AsyncSqliteSaver` due to an open bug (langchain#5790) and suggests simply invoking the compiled graph directly via `agent.py`.
**The Fix:** While accurate, invoking the graph directly via `agent.py` means you lose the visual tracing UI that makes LangGraph powerful for debugging cyclic dependencies.
Instead of abandoning LangGraph Studio/CLI, use the official workaround: configure LangGraph Studio via `langgraph.json` to connect to a custom Postgres/SQLite instance instead of relying on the CLI's default in-memory runner. This allows you to debug your curriculum DAG visually without sacrificing persistence.

### Summary of Improvements to Merge into the Plan

1. **Add STT Normalization to Phase 1:** Pin `FasterWhisperSTT` kwargs to enforce verbatim transcriptions.
2. **Upgrade Phase 2 (TTS):** Change `KokoroChunkedStream` to `KokoroSynthesizeStream` for sub-sentence clause-level audio emission.
3. **Patch Phase 6 (Reconsideration):** Ensure async tools append a `ChatMessage(role="system", ...)` to the `chat_ctx` upon completion so the LLM remains aware of what is on the user's screen.
4. **Update Hardware Guidelines:** Enforce a strict job-queue pause for Tier 2 whenever Tier 1 is active on constrained GPUs to prevent Ollama VRAM thrashing.