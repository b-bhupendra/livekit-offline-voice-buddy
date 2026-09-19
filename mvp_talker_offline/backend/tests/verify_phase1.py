import os
import sys
import json
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines import rag_store
from engines import syllabus_tracker
from engines import quiz_engine
from engines import simulation_engine
import agent

class TestPhase1Backend(unittest.TestCase):
    def setUp(self):
        self.rag = rag_store.RAGStore()
        self.tracker = syllabus_tracker.SyllabusTracker(user_id=f"test_user_{uuid.uuid4().hex[:6]}")
        self.quizzer = quiz_engine.QuizEngine(syllabus_tracker=self.tracker)
        self.simulation = simulation_engine.SimulationEngine(rag_store=self.rag)

    def test_01_rag_hybrid_search(self):
        """Test hybrid vector + FTS search across ingested knowledge base."""
        counts = self.rag.count_chunks()
        print(f"\n[Test 1] RAG chunks in store: {counts}")
        self.assertGreater(counts.get("reference_book", 0), 10, "Reference books must be indexed")
        self.assertGreater(counts.get("udemy_lecture", 0), 100, "Udemy lectures must be indexed")

        results = self.rag.hybrid_search("stative verbs progressive", top_k=2)
        self.assertGreater(len(results), 0, "Hybrid search must return results")
        print(f"[Test 1] Hybrid search top result: {results[0]['source_title']} -> {results[0]['text'][:80]}...")

    def test_02_quiz_bank_depth_and_isomorphic_mutation(self):
        """Test 40-50 question banks and isomorphic question mutation."""
        bank = self.quizzer.load_quiz_bank(1)
        print(f"\n[Test 2] Chapter 1 quiz bank size: {len(bank)}")
        self.assertGreaterEqual(len(bank), 35, "Bank must have comprehensive question coverage")

        sample_q = bank[0]
        mutated = self.quizzer.mutate_isomorphic(sample_q)
        print(f"[Test 2] Original: {sample_q['question']}")
        print(f"[Test 2] Mutated Isomorphic: {mutated['question']}")
        self.assertTrue(mutated.get("is_isomorphic"), "Must be tagged as isomorphic")

        # Test evaluation with correct answer
        eval_correct = self.quizzer.evaluate_answer(sample_q, sample_q["correct_answer"])
        self.assertTrue(eval_correct["is_correct"], "Correct answer must pass")

        # Test evaluation with incorrect answer triggers isomorphic mutation
        eval_wrong = self.quizzer.evaluate_answer(sample_q, "completely wrong answer")
        self.assertFalse(eval_wrong["is_correct"], "Wrong answer must fail")
        self.assertIn("isomorphic_question", eval_wrong, "Failure must generate isomorphic question")

    def test_03_syllabus_linear_gating(self):
        """Test that linear progression strictly gates advancing before coursework and quiz are complete."""
        state = self.tracker.get_state()
        print(f"\n[Test 3] Initial Chapter: {state['current_chapter_idx']}, Stage: {state['current_stage']}")
        self.assertFalse(self.tracker.can_advance(), "Cannot advance initially")

        # Marking only coursework is not enough
        self.tracker.mark_coursework_completed()
        self.assertFalse(self.tracker.can_advance(), "Cannot advance without passing milestone quiz")

        # Marking quiz passed allows advancement
        self.tracker.mark_quiz_passed(95.0)
        self.assertTrue(self.tracker.can_advance(), "Can advance once both are complete")

        advanced = self.tracker.advance_to_next_chapter()
        self.assertTrue(advanced, "Advancing must succeed")
        new_state = self.tracker.get_state()
        print(f"[Test 3] Advanced to Chapter: {new_state['current_chapter_idx']}")
        self.assertEqual(new_state["current_chapter_idx"], 2, "Must advance linearly to Chapter 2")

    def test_04_anti_hallucination_dispute_and_web_search(self):
        """Test anti-hallucination fact-checking and register differentiation."""
        claim = "none of them were is accepted"
        ruling = self.simulation.handle_answer_contention(claim)
        print(f"\n[Test 4] Contention Ruling Verdict: {ruling['verdict']}")
        print(f"[Test 4] Analysis: {ruling['analysis'][:120]}...")
        self.assertIn("VALID_REGISTER_DIFFERENCE", ruling["verdict"], "Should recognize register distinction")

    def test_05_in_process_agent_tools(self):
        """Verify that agent.py has all FastMCP tools folded in-process with RunContext."""
        tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in agent.in_process_tools]
        print(f"\n[Test 5] In-process agent tools: {tool_names}")
        expected = [
            "query_grammar_rag",
            "trigger_quiz",
            "generate_quiz",
            "dispute_answer",
            "get_learner_progress",
            "generate_revision_notes",
            "advance_chapter",
            "log_learner_recast",
            "save_conversation_turn",
            "search_web_grammar"
        ]
        for exp in expected:
            self.assertIn(exp, tool_names, f"Tool {exp} must be registered in agent in-process tools")

if __name__ == "__main__":
    unittest.main()
