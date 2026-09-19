# Buddy: Verified Implementation Plan
## Two-Tier Voice Co-Learner + Async Curriculum Compiler

This plan reconciles two prior reviews of the codebase — the working audit/design session in this conversation, and the independently-generated "Comprehensive Project Viability and Tutor Assessment" (Gemini) — against the **actual current APIs** of LiveKit Agents, LangGraph, and Ollama's LangChain integration, verified via documentation search rather than assumed from training data. Where a proposal from either review turned out to rest on an outdated or invented API, that's flagged and corrected below. Where research surfaced a *better*-fitting native mechanism than what either review proposed, that's called out explicitly.

---

## 0. Reconciling the two reviews

Both reviews converge on the same diagnosis — confirmed independently in this conversation earlier: the WebRTC/model plumbing (LiveKit, Kokoro, ChromaDB) is sound engineering; the pedagogical runtime is what's broken (disconnected LangGraph/Chroma stores, placeholder-to-thin quiz banks, missing `InlineCanvasLectureCard`, the mic-publish bug, the `_audio_server_proc` `NameError`, unpinned deps). Both land on the same target shape: a **fast, tool-free conversational tier** and a **slow, tool-heavy authoring tier**, decoupled by latency budget rather than by feature.

Two places where research changes the recommendation from what was proposed:

1. **Job durability.** The Gemini review proposes a hand-rolled `curriculum_jobs` SQLite table with `WAL` mode and manual `UPDATE ... RETURNING *` leasing. This works, but it's reinventing a mechanism LangGraph already ships, and since the codebase is *already* committed to LangGraph for orchestration, using its own checkpointer is less code and more idiomatic. See §2.1.
2. **TTS latency fix.** Both reviews correctly identify `audio_server.py`'s full-WAV-over-HTTP round trip as the latency floor, and both propose streaming PCM instead. Research confirms LiveKit Agents has a first-class plugin interface for exactly this (`tts.TTS` / `tts.SynthesizeStream` / `tts.AudioEmitter`) rather than requiring a bespoke custom audio track — see §2.2, this is a cleaner fix than either review's sketch.

Everything else below is additive detail and a concrete phase plan, not a contradiction of either prior document.

---

## 1. Confirmed root causes (do not re-litigate — fix these first)

These are the bugs independently verified against the actual codebase across this conversation and cross-checked against the Gemini PDF. Treat this as the fixed baseline before any architecture work begins — none of Tier 1/Tier 2 below will be testable until these are closed:

| # | Bug | File | Fix |
|---|---|---|---|
| 1 | Mic never published after room connects | `useLiveKit.ts` | Move `setMicrophoneEnabled` call into the `RoomEvent.Connected` handler, not a `useEffect` keyed only on `[isVoiceActive]` |
| 2 | `_audio_server_proc` used via `global` but never initialized at module scope → `NameError` on shutdown | `agent.py` | Add `_audio_server_proc: Optional[subprocess.Popen] = None` at module level |
| 3 | `LangGraphTutorEngine._init_knowledge_store()` queries a `rag_chunks` SQLite table that was never created after the move to ChromaDB | `langgraph_tutor_graph.py` | Point it directly at `RAGStore()._col.get(...)`, or better — see §2.1, this whole method becomes unnecessary once LangGraph nodes call `RAGStore` directly at retrieval time instead of pre-loading everything into a separate in-memory store |
| 4 | `verify_phase1.py` asserts on `counts.get("reference_book", 0)` but `count_chunks()` returns only `{"total": N}` | `rag_store.py` / `verify_phase1.py` | Make `count_chunks()` delegate to the existing `count_by_source()` and merge in `"total"`, so both call sites work |
| 5 | `InlineCanvasLectureCard.tsx` imported in `App.tsx`, absent from the codebase | frontend | Build it — see §4, this becomes the `DynamicCanvasRenderer` |
| 6 | Missing `requirements.txt` entries used at runtime: `pypdf`, `duckduckgo-search`, `langgraph` | `requirements.txt` | Pin all three; also pin `langgraph-checkpoint-sqlite` for §2.1 |
| 7 | Hardcoded absolute path `UDEMY_DIR = "/home/bhupendra/Videos/..."` | `knowledge_ingestor.py` | Replace with an env var or CLI arg, no personal path in source |
| 8 | Three divergent quiz-bank generations (fake placeholders, thin `curriculum_banks_generator.py` at ~2.8 q/chapter average, and the one real Chapter 1 bank) with run-order-dependent overwrite behavior | `knowledge_ingestor.py`, `curriculum_banks_generator.py` | Superseded entirely by §3's dynamic isomorphic question engine — don't keep patching the static banks, replace the mechanism |

---

## 2. Tier 1: The fast conversational loop ("Buddy")

**Target: sub-700ms turn latency, ideally 300–500ms time-to-first-audio.** This tier is a pure conversational peer — it authors nothing, and it queries the curriculum store read-only.

### 2.1 Zero-tool fast path — verified mechanism

LiveKit Agents' `Agent.update_tools()` is a real, documented method (confirmed against current docs): it replaces an agent's entire tool list at runtime, and the framework logs the change into conversation history as an `AgentConfigUpdate` so the LLM has visibility into the swap. This is the correct mechanism for the Buddy ↔ Tutor mode split both reviews proposed — no need to build a custom mode-switch layer:

```python
# On entering casual conversation:
await agent.update_tools([])  # zero schemas — nothing for Ollama to parse on prefill

# On "teach me X" / explicit study trigger:
await agent.update_tools(IN_PROCESS_TOOLS)  # full toolset restored
```
Docs also confirm tools can execute in the background "letting the agent keep talking while long-running work completes" — this is the sanctioned mechanism for the latency-masking pattern in §2.3 (Buddy says "let me pull that up" while a tool's async body is still running), not a workaround.

**Model size**: both reviews converge on dropping to a 1.5B–3B quantized model for this tier specifically (the Gemini review suggests `qwen2.5:3b` at `q4_k_m`, ~2.5GB VRAM). Confirm this against your actual hardware in Phase 2 testing — this is the single biggest lever on latency, bigger than the tool-stripping.

### 2.2 Real streaming TTS instead of WAV-over-HTTP — verified mechanism

Both reviews correctly diagnose `audio_server.py` (build full WAV in memory, return over HTTP, LiveKit waits for the complete file) as a latency floor of ~1.5–2s regardless of what else is optimized. Research confirms LiveKit Agents ships a proper plugin base class for this exact problem: `livekit.agents.tts.TTS`, with `SynthesizeStream` (streamed, e.g. websocket-driven) and `ChunkedStream` (one-shot) subclasses, both writing into a `tts.AudioEmitter`. The emitter takes raw PCM directly — **no WAV wrapper, no base64, no HTTP round trip needed** — a plugin calls `output_emitter.initialize(sample_rate=..., stream=True, mime_type="audio/pcm")` then pushes frames as they're generated.

This means the correct fix isn't "stream WAV chunks over a custom endpoint" (which is what both reviews' code sketches do) — it's **write Kokoro as a real `tts.TTS` plugin subclass**, so it plugs into `AgentSession(tts=...)` the same way any first-party plugin does, gets automatic interruption/barge-in handling from the framework (this is handled at the `AudioEmitter`/session level, not something you re-implement), and never touches an HTTP server at all for the live path:

```python
from livekit.agents import tts
from livekit import rtc
import numpy as np

class KokoroTTS(tts.TTS):
    def __init__(self, voice="af_heart", sample_rate=24000):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=True),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self._kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
        self._voice = voice

    def synthesize(self, text: str, *, conn_options=None) -> "KokoroChunkedStream":
        return KokoroChunkedStream(tts=self, input_text=text, conn_options=conn_options)

class KokoroChunkedStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=self._tts.sample_rate,
            num_channels=1,
            mime_type="audio/pcm",
        )
        # Kokoro generates per-sentence numpy arrays already; push each as it's ready
        for sentence in split_sentences(self.input_text):
            samples, sr = self._tts._kokoro.create(sentence, voice=self._tts._voice, lang="en-us")
            output_emitter.push(samples.astype(np.int16).tobytes())
```
Once this exists, `audio_server.py` and its `/v1/audio/speech` HTTP hop can be deleted for the live path entirely — it's only still useful, if at all, as a standalone dev tool for previewing voices outside a session. The "studio quality" upgrade path (swap `af_heart`/`amy-high` for a heavier model like ChatTTS/F5-TTS for pre-rendered lecture audio) is a separate, offline concern — see §3.4 — and does not need to implement this streaming interface at all, since pre-rendered clips are just files.

### 2.3 Latency masking for tool-triggered background work

When Buddy's fast tier triggers a Tier 2 job (a lecture doesn't exist yet, a reconsideration was requested), the tool function should:
1. Return immediately with a short spoken bridge line baked into the tool's return value (the LLM reads this back verbatim or paraphrases it), matching the pattern LiveKit's own docs describe for background tool execution.
2. Enqueue the actual work (§3) as a LangGraph invocation, not a raw `asyncio.create_task` with no crash recovery.
3. Push the result to the room via `send_room_text(..., "genui", ...)` once ready, gated on the session being in a natural pause (check `agent_state` before pushing, as discussed earlier) so it doesn't cut Buddy off mid-sentence.

---

## 3. Tier 2: The async curriculum/authoring engine

**Target: no latency ceiling — seconds to an hour, whatever a thorough job needs.** This tier never touches the live voice path.

### 3.1 Durable execution — use LangGraph's own checkpointer, not a hand-rolled queue

Since the codebase already depends on LangGraph, the idiomatic way to get "survives a crash 45 minutes into an hour-long build" is **`AsyncSqliteSaver`** (`from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver`), compiled into the curriculum-authoring graph:

```python
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

conn = await aiosqlite.connect("data/curriculum_checkpoints.db")
checkpointer = AsyncSqliteSaver(conn=conn)
curriculum_graph = builder.compile(checkpointer=checkpointer)

# Each chapter/node build is its own thread_id — a crash only loses the in-flight node,
# not the whole run, because LangGraph persists state after every node transition:
config = {"configurable": {"thread_id": f"curriculum-build-ch{chapter_idx}"}}
await curriculum_graph.ainvoke({"source_chunks": chunks}, config)
```
This gets you per-node checkpointing, resumability, and a full history of intermediate states **for free**, without maintaining a bespoke `curriculum_jobs` table with manual status/lease columns as the Gemini review sketches. One caveat surfaced in research: `langgraph dev` (the CLI dev server) ignores a configured checkpointer and forces an in-memory runtime — this only matters if you're using `langgraph dev` for iteration; running the compiled graph directly from `agent.py` (which is what this project does) is unaffected.

Progress reporting to the frontend during a long build reuses the existing `push_periodic_progress()` / `"progress"` text-stream channel, now driven by LangGraph's checkpoint events (each node completion is a natural point to push an update) rather than a custom polling loop.

### 3.2 Grounded curriculum synthesis with verified structured output

Both reviews propose the LLM freely generating JSON for lecture/quiz content. The failure mode neither fully addresses: **prompt-only JSON generation from a small local model is unreliable** — malformed JSON, missing fields, inconsistent schemas across chapters. Research confirms the fix: `ChatOllama.with_structured_output(schema, method="json_schema")` (from `langchain_ollama`, added in `langchain-ollama>=0.2.2`, `json_schema` became the default method in `0.3.0`) routes through Ollama's native `format` parameter, so the *model server itself* constrains generation to match a Pydantic schema — not just a prompt instruction the model might ignore:

```python
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
from typing import List

class CurriculumNode(BaseModel):
    node_id: str
    title: str
    core_concept: str
    prerequisites: List[str]
    lecture_paragraphs: List[str] = Field(description="2-3 grounded paragraphs")
    canvas_type: str  # one of the 5 widget primitives, see §4
    canvas_config: dict
    citations: List[str]

model = ChatOllama(model="qwen-buddy-author", temperature=0.2)
structured_model = model.with_structured_output(CurriculumNode, method="json_schema")
node = structured_model.invoke(authoring_prompt)  # returns a validated CurriculumNode instance directly
```
This is a stronger guarantee than either review's plain "the LLM writes JSON" sketch, and it's what makes the deterministic-gate step in §3.3 actually catch something meaningfully different from schema errors (schema errors are now handled at generation time; the gate is free to focus on *content* correctness).

Known gotcha from research worth testing early: Ollama tool/structured-output support quality varies by exact model — `qwen2.5` family generally has good native tool/JSON support, but verify empirically against whatever specific quantization you settle on for the authoring model, since this is a documented pain point in the LangChain/Ollama ecosystem (several open issues about `bind_tools`/structured output reliability with smaller or older Ollama models).

### 3.3 Critique pipeline — deterministic gate + distinct critic model

Confirmed sound in the Gemini review, worth keeping as specified:
1. **Deterministic gate (no LLM cost):** the Pydantic validation from §3.2 already gives you this for free at generation time; add a second pass that regex/substring-checks every `citations` entry actually appears in the retrieved ChromaDB chunks passed into the prompt — reject and retry if a citation doesn't trace back to real source text.
2. **Model diversity for semantic critique:** don't have `qwen-buddy-author` grade its own output — self-confirmation bias is real and well documented for LLM self-critique. Use a distinct, smaller model (the review's `Llama-3.2-3B`/`Gemma-2-2B` suggestion is reasonable) purely as an auditor, or route this one pass to a cloud API since it's async and never touches the live voice path.

### 3.4 Studio-quality pre-rendered audio

Once a node's `lecture_paragraphs` are finalized and pass critique, synthesize its audio with a *heavier, higher-quality* TTS model than the live conversational voice — ChatTTS, F5-TTS, or a Kokoro voice tuned for warmth (`af_heart`/`af_bella` per the Gemini review's voice comparison table) — and cache the resulting audio file on disk, linked to the node in the curriculum store. This step does **not** need the streaming `tts.TTS` plugin interface from §2.2 at all, since it's a one-shot batch render, not a live session — a plain synchronous call to whichever TTS library, writing a `.wav`/`.mp3` to `data/lecture_audio/{node_id}.wav`, is sufficient. At delivery time, Tier 1 just plays the cached file — zero synthesis latency for previously-authored content.

### 3.5 Variant storage and pruning

As designed earlier in this conversation: key by `(node_id, interpretation_style)`, not overwrite. Add the Gemini review's concrete pruning policy — it's a reasonable, implementable default:
- Track `impressions_count`, `learner_satisfaction_score`, `last_accessed_at` per variant.
- Cap at **K=3 variants per node** (e.g. `canonical`, plus two most-requested alternate framings).
- On a 4th distinct variant request, evict the lowest-scoring one rather than growing unboundedly.
- **Promotion trigger:** if a variant's mastery/satisfaction metrics exceed the canonical version's, auto-promote it to become the new default — this is what actually closes the "living curriculum improves over time" loop, not just accumulating alternates.

### 3.6 Dynamic isomorphic question generation — replaces static banks entirely

This is the fix for finding #8 in §1 (three divergent, thin quiz-bank generations). Stop maintaining `_generate_chapter_bank` and `curriculum_banks_generator.py` as static content at all. Instead, generate questions the same way as lectures — through the structured-output pipeline in §3.2, grounded in the node's retrieved chunks, validated by the same critique gate. When a learner fails a question, generate a fresh isomorphic variant on demand (same underlying grammatical constraint, different surface words) rather than picking from a fixed pool — this is what the Gemini review's `CritiqueRequest`/isomorphic-mutation sketch gets right, and it eliminates the "only 2-8 real questions per chapter" ceiling structurally, since there's no longer a fixed bank to run out of.

---

## 4. Frontend: generalized GenUI

### 4.1 Widget primitive consolidation

Confirmed good idea from the Gemini review: collapse the six grammar-specific `canvas_type`s into fewer subject-agnostic primitives. Recommended mapping (adopting the Gemini review's version, which is well-reasoned):

| Existing hardcoded type | Generalized primitive |
|---|---|
| `particle_classifier` | `ClassifierBoard` — sorting items into buckets |
| `concord_balance`, `workplace_matrix` | `ComparisonMatrix` — contrasting pairs/registers |
| `compound_builder`, `noun_hierarchy` | `HierarchyTree` — token trees, head-modifier links |
| `repetition_flow` | `FlowSequence` — step-by-step cadence/sequence |

A well-defined 4-5 primitive schema is something a small local model can reliably emit structured config for (per §3.2's schema validation); an unbounded set of bespoke component shapes is not.

### 4.2 Build `InlineCanvasLectureCard` as a polymorphic dispatcher

This directly resolves the missing-component bug from §1. The dispatcher is intentionally dumb — it has no domain logic, it just routes `canvas_type` → the right widget:

```tsx
// VisualsFrontend/src/components/InlineCanvasLectureCard.tsx
import { ClassifierBoard } from './widgets/ClassifierBoard';
import { ComparisonMatrix } from './widgets/ComparisonMatrix';
import { HierarchyTree } from './widgets/HierarchyTree';
import { FlowSequence } from './widgets/FlowSequence';

export const InlineCanvasLectureCard: React.FC<{ canvasType: string; config: any }> = ({ canvasType, config }) => {
  switch (canvasType) {
    case 'classifier': return <ClassifierBoard data={config} />;
    case 'matrix': return <ComparisonMatrix data={config} />;
    case 'tree': return <HierarchyTree data={config} />;
    case 'flow': return <FlowSequence data={config} />;
    default: return <div className="p-4 rounded border">Unsupported canvas type: {canvasType}</div>;
  }
};
```
Each of the four widget components (`ClassifierBoard`, etc.) is genuinely new work — they don't exist yet either, only the old grammar-specific `CanvasLectureCard`/`GrammarMovement` components do. Budget real frontend time for these four, not just the dispatcher shell.

### 4.3 Bidirectional canvas interactivity via RPC — verified mechanism

For canvas interactions that need to reach back into the LangGraph state machine (dragging a token, clicking a classifier bucket), the verified mechanism is LiveKit's RPC system: the agent pre-registers a handler with `room.local_participant.register_rpc_method(...)`, and the frontend calls it with `room.localParticipant.performRpc({destinationIdentity, method, payload})`, awaiting a structured response. This is the same mechanism LiveKit's own docs use for forwarding tool calls to a frontend — it's the correct, documented pattern for this, not a custom data-channel protocol:

```python
# Backend, registered once at session start
@ctx.room.local_participant.register_rpc_method("canvas_interaction")
async def handle_canvas_interaction(data: RpcInvocationData) -> str:
    payload = json.loads(data.payload)
    # e.g. update tracker state, decide if answer was correct, etc.
    result = tracker.record_interaction(payload["node_id"], payload["action"])
    return json.dumps(result)
```
```ts
// Frontend, on a drag/click event inside ClassifierBoard
const response = await room.localParticipant.performRpc({
  destinationIdentity: agentIdentity,
  method: "canvas_interaction",
  payload: JSON.stringify({ node_id, action: "drop", item, bucket }),
});
```

---

## 5. Priority execution order

Phases are sequential — each depends on the previous one being stable, since later phases build on the earlier ones' plumbing.

| Phase | Goal | Key work | Exit criteria |
|---|---|---|---|
| **1** | Runtime stability | Fix all 8 items in §1's bug table; pin dependencies; delete/fix the shutdown `NameError` path | `verify_phase1.py` passes; app boots and shuts down cleanly with no manual hotfixes |
| **2** | Tier 1 fast path | Build `KokoroTTS` streaming plugin (§2.2); swap in the small conversational model; wire `update_tools([])`/`update_tools(FULL)` mode switch (§2.1) | Measured time-to-first-audio consistently under ~700ms in casual conversation, verified with real logging, not estimated |
| **3** | Tier 2 skeleton | Compile the curriculum-authoring LangGraph with `AsyncSqliteSaver` (§3.1); wire `ChatOllama.with_structured_output` for one node type end-to-end (§3.2) | A single chapter/node can be authored, checkpointed, and resumed after a simulated crash |
| **4** | Frontend GenUI | Build `InlineCanvasLectureCard` + the four widget primitives (§4.1-4.2); wire RPC interactivity (§4.3) | A generated node's canvas renders correctly for all four primitive types, and a canvas interaction round-trips to the backend |
| **5** | Critique + question engine | Deterministic + model-diversity critique gate (§3.3); dynamic isomorphic question generation replacing static banks (§3.6); studio audio pre-render (§3.4) | Full pipeline: source chunks in → critiqued, cited lecture + quiz + pre-rendered audio out, for a full chapter, unattended |
| **6** | Variant/reconsideration loop | `request_reinterpretation` tool wired to the Tier 2 pipeline; variant storage + pruning policy (§3.5) | Asking Buddy for a different explanation produces a persisted, reusable variant without blocking the live conversation |
| **7** | Scale test | Run the full pipeline unattended across all 18 chapters / whatever source corpus is loaded, timed | Confirms real wall-clock cost of a full course build, and surfaces any node-level failures before relying on it live |

---

## 6. Open items still worth a second opinion

Carried over from the earlier discussion, now narrowed by the research above:

1. **Hardware budget for genuine two-model parallelism** — both reviews flag this correctly (a small conversational model + a larger authoring model sharing one GPU/CPU will contend). This plan doesn't resolve it; it needs to be measured against your actual machine, not assumed. The cloud-API-for-Tier-2-only fallback both reviews suggest remains the simplest way to sidestep this entirely.
2. **Ollama structured-output reliability at your chosen quantization** — flagged in §3.2 as a documented ecosystem pain point; worth an isolated smoke test (a few dozen synthetic authoring prompts against `CurriculumNode`) before building the rest of Tier 2 on top of it.
3. **`langgraph dev` vs. direct invocation** — if any part of the build/iteration workflow ends up using the LangGraph CLI dev server rather than running the compiled graph from `agent.py` directly, the checkpointer-ignoring behavior noted in §3.1 will silently break persistence testing. Worth a one-line note in team docs so it isn't rediscovered the hard way.
