#!/usr/bin/env python3
"""
Verification Script for Phase 2: Pedagogical Engine Correctness.
Tests:
  1. Embedding Failure Fallback (rag_store.py)
  2. Offline Dispute Fallback with textbook fallback (simulation_engine.py)
  3. Isomorphic Mutation Auditing & Drift Metrics in SQLite (syllabus_tracker.py)
  4. Learner State Summary Synchronization (syllabus_tracker.py & agent.py)
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is in python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from engines.rag_store import RAGStore, EmbeddingServiceUnavailable
from engines.syllabus_tracker import SyllabusTracker
from engines.simulation_engine import SimulationEngine

class TestPhase2PedagogicalEngine(unittest.TestCase):

    def setUp(self):
        self.rag = RAGStore()
        self.tracker = SyllabusTracker(user_id="test_verification_user")
        self.sim = SimulationEngine(rag_store=self.rag)

    def test_01_embedding_failure_fallback(self):
        """1. Verify distinct return path and exception when embedding service is down."""
        # Point to invalid Ollama port to simulate network/service downtime
        bad_rag = RAGStore()
        bad_rag.embed_url = "http://127.0.0.1:59999"

        # A) With raise_on_error=True, must raise EmbeddingServiceUnavailable
        with self.assertRaises(EmbeddingServiceUnavailable):
            bad_rag.get_embedding("Test grammar query", raise_on_error=True)

        self.assertFalse(bad_rag.is_embedding_available)
        self.assertEqual(bad_rag.embedding_status, "unreachable")
        self.assertIsNotNone(bad_rag.last_embedding_error)

        # B) With raise_on_error=False, returns None without crashing
        res = bad_rag.get_embedding("Test grammar query", raise_on_error=False)
        self.assertIsNone(res)
        status = bad_rag.get_embedding_status()
        self.assertFalse(status["is_available"])
        self.assertEqual(status["status"], "unreachable")
        print(" [PASS] Embedding failure fallback handles outage with distinct diagnostics.")

    def test_02_offline_dispute_fallback(self):
        """2. Verify dispute handler catches DDGS failure and falls back to local textbook chunks."""
        # Mock DDGS to simulate search engine failure / offline condition
        with patch("engines.simulation_engine.DDGS") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.side_effect = Exception("ConnectionRefusedError: No internet access in offline sandbox")
            mock_ddgs.return_value = mock_instance

            res = self.sim.handle_answer_contention(
                user_claim="I believe 'neither of them are' is grammatically correct in modern English",
                original_question="Neither of the two candidates were chosen."
            )

            self.assertTrue(res.get("offline_mode"), "Dispute handler should mark offline_mode=True on failure")
            self.assertIn("100% OFFLINE MODE", res.get("system_prompt_instruction", ""))
            self.assertIn("local textbook", res.get("system_prompt_instruction", "").lower())
            
            snippets = res.get("web_search_snippets", [])
            self.assertTrue(len(snippets) > 0, "Should fall back to local textbook citations")
            self.assertTrue(any("Oxford Guide" in s["title"] or "Arihant" in s["title"] for s in snippets))
            print(" [PASS] Offline dispute fallback cleanly recovers and queries local textbook chunks.")

    def test_03_isomorphic_mutation_auditing(self):
        """3. Verify SQLite audit logs (original_question, mutated_question, student_pass/fail) and calculates drift."""
        # Insert test mutation audit triples
        self.tracker.log_isomorphic_mutation(
            original_q_id="test_q1",
            mutated_q_id="test_q1_mut1",
            original_text="Neither of the books were available.",
            mutated_text="Neither of the candidates were selected.",
            rule_citation="Oxford Guide Ch 2 Rule 12",
            student_pass=True
        )
        self.tracker.log_isomorphic_mutation(
            original_q_id="test_q1",
            mutated_q_id="test_q1_mut2",
            original_text="Neither of the books were available.",
            mutated_text="Neither of the managers were notified.",
            rule_citation="Oxford Guide Ch 2 Rule 12",
            student_pass=False
        )

        audits = self.tracker.get_isomorphic_audits(limit=10)
        self.assertTrue(len(audits) >= 2)
        latest = audits[0]
        self.assertIn("original_text", latest)
        self.assertIn("mutated_text", latest)
        self.assertIn("student_pass", latest)
        self.assertIn("rule_citation", latest)

        # Verify drift metrics
        drift = self.tracker.audit_mutation_drift()
        self.assertGreaterEqual(drift["total_mutations"], 2)
        self.assertIn("pass_rate", drift)
        self.assertEqual(drift["status"], "active_monitoring")
        print(" [PASS] Isomorphic mutation logging & drift monitoring correctly stored in SQLite.")

    def test_04_sync_learner_state_summary(self):
        """4. Verify get_learner_summary provides complete authoritative curriculum state."""
        summary = self.tracker.get_learner_summary()
        self.assertIn("active_chapter", summary)
        self.assertIn("stage", summary)
        self.assertIn("coursework_completed", summary)
        self.assertIn("quiz_passed", summary)
        self.assertIn("cumulative_accuracy", summary)
        self.assertIn("roadmap", summary)
        self.assertIn("drift_audit", summary)
        self.assertEqual(len(summary["roadmap"]), 18)
        print(" [PASS] Authoritative learner state summary correctly structured.")

if __name__ == "__main__":
    unittest.main()
