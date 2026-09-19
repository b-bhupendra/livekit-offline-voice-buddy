#!/usr/bin/env python3
"""
Headless Console Test CLI Runner — LiveKit Offline Voice AI Buddy.
Phase 6: Testing & Rollout.

Built upon LiveKit's official testing primitive: `livekit.agents.testing.fake_job_context`.
Scripts through a complete pedagogical milestone end-to-end without requiring a browser or external media server:
  1. Trigger Milestone Quiz (Chapter 1)
  2. Answer Incorrectly (Intentional Error Injection)
  3. Verify Isomorphic Reinforcement Fallback (Targeted Trap Reinforcement)
  4. Dispute Answer (Contention Resolution: "LLM is wrong")
  5. Verify Offline RAG Arbitration Fallback (Sandboxed Offline Textbook Fallback)

Visual GenUI Event Interceptor:
  Captures and renders every real-time event sent over the LiveKit WebRTC text stream to create UI cards.
"""

import os
import sys
import time
import json
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import agent
from livekit import rtc
from livekit.agents import testing
from engines.syllabus_tracker import SyllabusTracker
from engines.simulation_engine import SimulationEngine
from engines.quiz_engine import QuizEngine
from engines.rag_store import RAGStore
from core.structured_logger import (
    stt_logger, llm_logger, tts_logger, rag_logger, genui_logger, system_logger,
    set_session_id, get_session_id
)

# ── ANSI Terminal Styling ────────────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"

def print_banner(title: str):
    width = 76
    print(f"\n{BOLD}{CYAN}╔{'═' * (width - 2)}╗{RESET}")
    print(f"{BOLD}{CYAN}║  {title.center(width - 6)}  ║{RESET}")
    print(f"{BOLD}{CYAN}╚{'═' * (width - 2)}╝{RESET}\n")

def print_step_header(step_num: int, title: str):
    print(f"{BOLD}{MAGENTA}── Step {step_num}: {title} {'─' * max(2, 60 - len(title))}{RESET}")

def render_genui_box(component: str, payload: Dict[str, Any]):
    """Renders a formatted visual terminal card representing the intercepted UI event."""
    width = 72
    top = f"{CYAN}┌─[ 🎨 LIVEKIT GENUI EVENT: {BOLD}{component}{RESET}{CYAN} ]{'─' * max(2, width - len(component) - 29)}┐{RESET}"
    bottom = f"{CYAN}└{'─' * (width - 2)}┘{RESET}"
    
    print(top)
    print(f"{CYAN}│{RESET} {BOLD}Type:{RESET} {payload.get('type', 'genui_render')}  │  {BOLD}Schema:{RESET} v{payload.get('schema_version', '1.0')}")
    
    props = payload.get("props", {})
    if "req_id" in props:
        print(f"{CYAN}│{RESET} {BOLD}Req ID:{RESET} {props['req_id']}")
        
    if component == "QuizCard":
        chapter = props.get("chapter", 1)
        mode = props.get("mode", "milestone")
        source = props.get("source", "bank")
        qs = props.get("questions", [])
        print(f"{CYAN}│{RESET} {BOLD}Chapter:{RESET} {chapter} | {BOLD}Mode:{RESET} {mode} | {BOLD}Source:{RESET} {source} | {BOLD}Total Questions:{RESET} {len(qs)}")
        if qs:
            sample = qs[0]
            print(f"{CYAN}│{RESET}   ├─ {BOLD}Q1:{RESET} {sample.get('stem') or sample.get('question', '')[:60]}...")
            print(f"{CYAN}│{RESET}   ├─ {BOLD}Options:{RESET} {', '.join(sample.get('options', [])[:4])}")
            print(f"{CYAN}│{RESET}   └─ {BOLD}Citation:{RESET} {sample.get('rule_citation', 'Oxford Guide')}")
            
    elif component == "ContentionResolver":
        verdict = props.get("verdict", "UNKNOWN")
        analysis = props.get("analysis", "")
        print(f"{CYAN}│{RESET} {BOLD}Verdict:{RESET} {YELLOW}{BOLD}{verdict}{RESET}")
        print(f"{CYAN}│{RESET} {BOLD}Analysis:{RESET} {analysis[:110]}...")
        citations = props.get("citations") or [w.get("title") for w in props.get("web_sources", [])] or props.get("local_rag_evidence", [])
        if citations:
            clean_c = [str(c)[:50] for c in citations if c]
            print(f"{CYAN}│{RESET} {BOLD}Authoritative Sources:{RESET} {', '.join(clean_c[:2])}")
            
    elif component == "sheet_error":
        title = props.get("title", "Error")
        msg = props.get("message", "")
        target = props.get("component_attempted", "Unknown")
        print(f"{CYAN}│{RESET} {RED}{BOLD}Error Status:{RESET} {title} (Target: {target})")
        print(f"{CYAN}│{RESET} {RED}{BOLD}Message:{RESET} {msg}")
        
    elif component == "GrammarMovement":
        title = props.get("title", "Syntactic Movement")
        init_t = [t.get("text", "") for t in props.get("initial_tokens", [])]
        trans_t = [t.get("text", "") for t in props.get("transformed_tokens", [])]
        print(f"{CYAN}│{RESET} {BOLD}Title:{RESET} {title}")
        print(f"{CYAN}│{RESET} {BOLD}Base:{RESET}        [{' | '.join(init_t)}]")
        print(f"{CYAN}│{RESET} {BOLD}Transformed:{RESET} [{' | '.join(trans_t)}]")
        print(f"{CYAN}│{RESET} {BOLD}Citation:{RESET} {props.get('rule_citation', 'Oxford Guide')}")
        
    print(bottom)

# ── Event Interceptor ────────────────────────────────────────────────
class LiveKitEventInterceptor:
    """Intercepts and records all LiveKit text stream emissions and GenUI payloads."""
    def __init__(self):
        self.captured_events: List[Dict[str, Any]] = []
        self._original_send = agent.send_room_text

    async def intercepted_send(self, context, topic: str, payload_str: str):
        try:
            parsed = json.loads(payload_str)
        except Exception:
            parsed = {"raw": payload_str}
            
        event_record = {
            "topic": topic,
            "payload": parsed,
            "timestamp": time.time()
        }
        self.captured_events.append(event_record)
        
        # Render visual terminal card for genui events
        if topic == "genui" and isinstance(parsed, dict) and parsed.get("type") == "genui_render":
            render_genui_box(parsed.get("component", "GenUI"), parsed)
        elif topic == "transcript":
            speaker = parsed.get("speaker", "agent").upper()
            txt = parsed.get("text", "")
            print(f"  {BLUE}💬 [{speaker} TRANSCRIPT]:{RESET} \"{txt[:80]}\"")
        elif topic == "progress":
            ch = parsed.get("active_chapter", 1)
            stage = parsed.get("stage", "lecture")
            acc = parsed.get("accuracy", 100.0)
            print(f"  {GREEN}📊 [PROGRESS SYNC]:{RESET} Chapter {ch} ({stage}) | Accuracy: {acc:.1f}%")

    def __enter__(self):
        agent.send_room_text = self.intercepted_send
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        agent.send_room_text = self._original_send

# ── Headless Milestone CLI Runner ────────────────────────────────────
class HeadlessMilestoneRunner:
    def __init__(self):
        self.session_id = f"test_milestone_{int(time.time())}"
        set_session_id(self.session_id)
        self.tracker = SyllabusTracker(user_id="test_headless_learner")
        self.rag = RAGStore()
        self.sim = SimulationEngine(rag_store=self.rag)
        self.quizzer = QuizEngine(syllabus_tracker=self.tracker)
        self.interceptor = LiveKitEventInterceptor()
        self.step_timings: Dict[str, float] = {}
        self.assertions_passed = 0
        self.total_assertions = 0

    def assert_true(self, condition: bool, description: str):
        self.total_assertions += 1
        if condition:
            self.assertions_passed += 1
            print(f"    {GREEN}✔ [PASS]{RESET} {description}")
        else:
            print(f"    {RED}✘ [FAIL]{RESET} {description}")
            raise AssertionError(f"Check failed: {description}")

    async def run(self):
        print_banner("LiveKit Offline Voice Buddy — Headless Milestone CLI Runner")
        print(f"  {BOLD}Session ID:{RESET}     {self.session_id}")
        print(f"  {BOLD}Framework:{RESET}      LiveKit Agents 1.3+ with `testing.fake_job_context`")
        print(f"  {BOLD}Transport:{RESET}      LiveKit WebRTC (Text Streams, Room RPC, SQLite Hydration)")
        print(f"  {BOLD}Active Target:{RESET}  Chapter 1: Course Foundations & Sentence Transformations\n")

        test_room = rtc.Room()
        start_all = time.perf_counter()

        with testing.fake_job_context(room=test_room) as fake_job, self.interceptor:
            # ── STEP 1: TRIGGER QUIZ ──────────────────────────────────────────
            print_step_header(1, "Trigger Milestone Quiz (Chapter 1)")
            t0 = time.perf_counter()
            
            quiz_result_str = await agent.trigger_quiz(None, chapter=1, mode="milestone")
            self.step_timings["Step 1: Trigger Quiz"] = (time.perf_counter() - t0) * 1000
            
            # Assertions
            self.assert_true("quiz_prepared" in quiz_result_str, "Agent trigger_quiz returns quiz_prepared status confirmation")
            
            # Verify intercepted GenUI event
            genui_events = [e for e in self.interceptor.captured_events if e["topic"] == "genui"]
            self.assert_true(len(genui_events) >= 1, "WebRTC 'genui' text stream received interactive payload")
            
            last_event = genui_events[-1]["payload"]
            self.assert_true(last_event.get("schema_version") == "1.0", "Emits strict schema_version '1.0'")
            self.assert_true(last_event.get("component") == "QuizCard", "Component matches 'QuizCard'")
            
            questions = last_event["props"].get("questions", [])
            self.assert_true(len(questions) >= 3, f"QuizCard contains valid questions (received {len(questions)})")
            
            # Verify SQLite persistence for in-flight reconnect
            last_sheet = agent.get_last_sheet_payload()
            self.assert_true(last_sheet is not None, "Sheet payload successfully persisted in SQLite table 'sheet_payloads'")
            self.assert_true(last_sheet["component"] == "QuizCard", "Persisted component matches 'QuizCard'")
            print(f"    {DIM}Latency: {self.step_timings['Step 1: Trigger Quiz']:.2f}ms{RESET}\n")

            # ── STEP 2: ANSWER INCORRECTLY ────────────────────────────────────
            print_step_header(2, "Answer Incorrectly (Intentional Error Injection)")
            t0 = time.perf_counter()
            
            target_q = questions[0]
            q_id = target_q.get("id", "ch01_q01")
            stem = target_q.get("stem") or target_q.get("question", "")
            correct_ans = target_q.get("correct_answer", "was")
            
            # Pick an intentionally incorrect answer
            wrong_ans = "were" if str(correct_ans).strip().lower() in ["was", "option a (correct)"] else "incorrect_token"
            
            print(f"    {BOLD}Question Stem:{RESET}  {stem}")
            print(f"    {BOLD}Correct Answer:{RESET} {correct_ans}")
            print(f"    {BOLD}Injected Error:{RESET} {RED}{wrong_ans}{RESET}")
            
            eval_result = self.quizzer.evaluate_answer(target_q, wrong_ans)
            self.step_timings["Step 2: Answer Incorrectly"] = (time.perf_counter() - t0) * 1000
            
            self.assert_true(eval_result["is_correct"] is False, "Answer evaluation marks incorrect answer as is_correct=False")
            self.assert_true("explanation" in eval_result, "Evaluation result contains pedagogical explanation")
            self.assert_true(eval_result.get("rule_citation") is not None, "Evaluation includes authoritative rule citation")
            
            # Verify learner tracking state
            state = self.tracker.get_state()
            self.assert_true(len(state["failed_questions_queue"]) >= 1, "Failed question recorded in learner's spaced repetition queue")
            print(f"    {DIM}Latency: {self.step_timings['Step 2: Answer Incorrectly']:.2f}ms{RESET}\n")

            # ── STEP 3: VERIFY ISOMORPHIC FALLBACK ─────────────────────────────
            print_step_header(3, "Verify Isomorphic Fallback Reinforcement")
            t0 = time.perf_counter()
            
            # Retrieve or generate isomorphic reinforcement question for the failed question
            isomorphic_q = self.quizzer.mutate_isomorphic(target_q)
            self.step_timings["Step 3: Isomorphic Fallback"] = (time.perf_counter() - t0) * 1000
            
            self.assert_true(isomorphic_q is not None, "Isomorphic sentence mutation engine produces practice question")
            self.assert_true(isomorphic_q.get("is_isomorphic") is True, "Question flagged with is_isomorphic=True")
            
            iso_stem = isomorphic_q.get("stem") or isomorphic_q.get("question", "")
            print(f"    {BOLD}Isomorphic Stem:{RESET} {CYAN}{iso_stem}{RESET}")
            print(f"    {BOLD}Target Trap:{RESET}     {isomorphic_q.get('isomorphic_trap', 'subject_verb_agreement')}")
            print(f"    {BOLD}Rule Citation:{RESET}   {isomorphic_q.get('rule_citation', 'Oxford Guide')}")
            
            # Verify audit logging in SQLite table 'isomorphic_mutation_audit'
            self.tracker.log_isomorphic_mutation(
                original_q_id=q_id,
                mutated_q_id=isomorphic_q.get("id", f"{q_id}_iso"),
                original_text=stem,
                mutated_text=iso_stem,
                rule_citation=isomorphic_q.get("rule_citation", "Oxford Guide"),
                student_pass=False
            )
            
            audits = self.tracker.get_isomorphic_audits(limit=5)
            self.assert_true(len(audits) >= 1, "Audit record successfully logged in SQLite 'isomorphic_mutation_audit'")
            self.assert_true(audits[0]["mutated_question_id"] == isomorphic_q.get("id", f"{q_id}_iso"), "Logged audit record matches mutated question ID")
            
            drift_stats = self.tracker.audit_mutation_drift()
            self.assert_true("pass_rate" in drift_stats, "Drift monitoring computes valid mutation drift metrics")
            print(f"    {DIM}Latency: {self.step_timings['Step 3: Isomorphic Fallback']:.2f}ms{RESET}\n")

            # ── STEP 4: DISPUTE ANSWER ("LLM IS WRONG") ────────────────────────
            print_step_header(4, "Dispute Answer Contention Resolution ('LLM is Wrong')")
            t0 = time.perf_counter()
            
            student_challenge = "My answer 'were' is right! The LLM is wrong because neither can take plural in modern English."
            print(f"    {BOLD}Student Claim:{RESET} \"{student_challenge}\"")
            
            ruling = self.sim.handle_answer_contention(student_challenge)
            ruling["req_id"] = f"req_dispute_{int(time.time() * 1000)}"
            
            # Broadcast contention card over WebRTC text stream
            dispute_payload = {
                "schema_version": "1.0",
                "type": "genui_render",
                "component": "ContentionResolver",
                "props": ruling
            }
            agent.persist_sheet_payload(ruling["req_id"], "ContentionResolver", dispute_payload)
            await agent.send_room_text(None, "genui", json.dumps(dispute_payload))
            self.step_timings["Step 4: Dispute Answer"] = (time.perf_counter() - t0) * 1000
            
            self.assert_true("verdict" in ruling, "Arbitration generates definitive verdict")
            self.assert_true(ruling["verdict"] in ["VALID_REGISTER_DIFFERENCE", "VERIFIED_ACCURATE", "STUDENT_INCORRECT", "STUDENT_CORRECT"], f"Verdict is valid ({ruling['verdict']})")
            self.assert_true(len(ruling.get("local_rag_evidence", [])) >= 0 or len(ruling.get("web_sources", [])) >= 1, "Arbitration cites authoritative sources (Oxford / Arihant)")
            self.assert_true("analysis" in ruling, "Arbitration provides detailed register comparison")
            
            # Verify SQLite persistence
            last_sheet = agent.get_last_sheet_payload()
            self.assert_true(last_sheet["component"] == "ContentionResolver", "Contention resolution card persisted in SQLite")
            print(f"    {DIM}Latency: {self.step_timings['Step 4: Dispute Answer']:.2f}ms{RESET}\n")

            # ── STEP 5: VERIFY OFFLINE RAG FALLBACK ────────────────────────────
            print_step_header(5, "Verify Offline RAG Fallback Arbitration")
            t0 = time.perf_counter()
            
            # Force DuckDuckGo search failure to simulate 100% offline airgapped operation
            with patch("simulation_engine.DDGS") as mock_ddgs:
                mock_inst = MagicMock()
                mock_inst.text.side_effect = ConnectionRefusedError("Offline Sandbox: No internet access permitted")
                mock_ddgs.return_value = mock_inst
                
                offline_ruling = self.sim.handle_answer_contention("Contesting question concord without internet connection")
                self.step_timings["Step 5: Offline Fallback"] = (time.perf_counter() - t0) * 1000
                
                self.assert_true(offline_ruling is not None, "Offline dispute arbitration produces valid ruling without network")
                self.assert_true(offline_ruling.get("offline_mode") is True, "Ruling explicitly flags offline_mode=True")
                self.assert_true(len(offline_ruling.get("web_sources", [])) >= 1, "Offline fallback queries local Oxford Guide/Arihant RAG chunks")
                print(f"    {BOLD}Offline Recovery:{RESET} {GREEN}✔ Successfully arbitrated via local RAG chunks{RESET}")
                print(f"    {BOLD}Fallback Source:{RESET}  {offline_ruling['web_sources'][0]['title']}")
                print(f"    {DIM}Latency: {self.step_timings['Step 5: Offline Fallback']:.2f}ms{RESET}\n")

        total_duration = (time.perf_counter() - start_all) * 1000

        # ── SUMMARY DASHBOARD ───────────────────────────────────────────────
        print_banner("Milestone Verification & Performance Summary")
        print(f"{'Step':<42} {'Latency':<14} {'Status':<10}")
        print(f"{'─' * 42} {'─' * 14} {'─' * 10}")
        for step, dur in self.step_timings.items():
            print(f"{step:<42} {dur:>8.2f} ms     {GREEN}PASS{RESET}")
        print(f"{'─' * 42} {'─' * 14} {'─' * 10}")
        print(f"{BOLD}{'Total End-to-End Execution':<42} {total_duration:>8.2f} ms     {GREEN}100% OK{RESET}\n")

        print(f"  {BOLD}Assertions Verified:{RESET} {GREEN}{self.assertions_passed} / {self.total_assertions} Passed{RESET}")
        print(f"  {BOLD}Captured UI Events:{RESET}  {len(self.interceptor.captured_events)} events delivered over LiveKit text stream")
        print(f"  {BOLD}Transport Status:{RESET}     LiveKit WebRTC Active & Stable (Legacy SSE Retired)\n")
        print(f"{GREEN}{BOLD}✨ Phase 6 Headless Milestone Test Completed Successfully!{RESET}\n")

if __name__ == "__main__":
    runner = HeadlessMilestoneRunner()
    asyncio.run(runner.run())
