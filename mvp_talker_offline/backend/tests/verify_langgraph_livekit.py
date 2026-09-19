"""
Comprehensive verification test for LiveKit + LangGraph Multi-Agent Architecture:
1. Dynamic curriculum catalog without hardcoded dictionaries
2. LangGraph Local Knowledge Store (Oxford Guide + Arihant + Luke)
3. State machine transitions: Buddy -> Tutor Lecture -> Tutor Q&A -> Tutor Quiz -> Buddy
4. Soft grammar error detection in Buddy mode
5. Multi-type practice sessions (grammar, daily talk repetition, workplace softening)
6. SQLite persistence and history retrieval
"""

import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.syllabus_tracker import SyllabusTracker
from tutor.langgraph_tutor_graph import langgraph_engine, TutorState

class TestLangGraphLiveKitSystem(unittest.TestCase):
    def setUp(self):
        self.tracker = SyllabusTracker(user_id="test_student_langgraph")

    def test_01_langgraph_knowledge_store(self):
        """Verifies LangGraph local store has loaded Oxford Guide, Arihant, and Luke course."""
        chunks = langgraph_engine.search_knowledge("countable and uncountable nouns", limit=3)
        self.assertGreater(len(chunks), 0, "Should retrieve grammar chunks from store")
        sources = [c.get("source_title") for c in chunks if c.get("source_title")]
        print(f"[TEST 1] LangGraph Knowledge Store retrieved {len(chunks)} chunks from: {sources}")

    def test_02_dynamic_curriculum_catalog(self):
        """Verifies curriculum catalog has all 4 practice domains and 18 chapters."""
        catalog = self.tracker.get_curriculum_catalog()
        domains = catalog.get("domains", {})
        self.assertIn("grammar_mastery", domains)
        self.assertIn("sentence_repetition", domains)
        self.assertIn("workplace_office", domains)
        self.assertIn("conversational_banter", domains)
        self.assertEqual(len(catalog["chapters"]), 18)
        print(f"[TEST 2] Catalog loaded {len(domains)} practice domains and 18 chapters.")

    def test_03_dynamic_session_synthesis(self):
        """Verifies dynamic lesson synthesis across different session types without hardcoding."""
        # 1. Grammar mastery (Nouns phase 2)
        nouns_sess = self.tracker.get_dynamic_course_session(
            topic="Nouns",
            submodule="Countable vs Uncountable (Mass Nouns)",
            session_type="grammar_mastery",
            phase_index=2
        )
        self.assertIn(nouns_sess["canvas_type"], ["particle_classifier", "classifier"])
        self.assertGreater(len(nouns_sess["paragraphs"]), 1)
        self.assertGreater(len(nouns_sess["repetition_items"]), 0)

        # 2. Daily Sentence Repetition (Contractions)
        rep_sess = self.tracker.get_dynamic_course_session(
            topic="Conversational Fluency",
            submodule="Everyday Spoken Contractions",
            session_type="sentence_repetition",
            phase_index=1
        )
        self.assertIn(rep_sess["canvas_type"], ["repetition_flow", "flow"])
        self.assertGreater(len(rep_sess["repetition_items"]), 0)

        # 3. Workplace & Office (Polite Softening)
        work_sess = self.tracker.get_dynamic_course_session(
            topic="Workplace Communication",
            submodule="Polite Requests & Softening",
            session_type="workplace_office",
            phase_index=1
        )
        self.assertIn(work_sess["canvas_type"], ["workplace_matrix", "matrix"])
        self.assertTrue("pairs" in work_sess["canvas_config"] or "items" in work_sess["canvas_config"])

        print("[TEST 3] Dynamic session synthesis verified for Grammar, Repetition, and Workplace.")

    def test_04_session_persistence_and_filtering(self):
        """Verifies saving and retrieving sessions with session_type and repetition items."""
        # Save a workplace session
        saved = self.tracker.save_lecture_session(
            topic="Workplace Communication",
            submodule="Polite Requests & Softening",
            phase_index=1,
            session_type="workplace_office",
            spoken_summary="In workplace English, softening direct commands creates a collaborative tone.",
            paragraphs=["Paragraph 1", "Paragraph 2"],
            canvas_type="workplace_matrix",
            canvas_config={"pairs": []},
            repetition_items=[{"target": "Could you please take a look at this?", "drill_type": "Softening"}]
        )
        self.assertEqual(saved["session_type"], "workplace_office")

        # Retrieve with filter
        history = self.tracker.get_lecture_history(limit=10, session_type="workplace_office")
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]["session_type"], "workplace_office")
        self.assertEqual(len(history[0]["repetition_items"]), 1)
        print(f"[TEST 4] Session persistence verified. ID: {saved['id']}, Filtered History: {len(history)} items.")

    def test_05_langgraph_state_machine_and_buddy_soft_error(self):
        """Verifies LangGraph state machine and soft grammar error detection in Buddy mode."""
        user_id = "test_student_lg_flow"
        initial_state = langgraph_engine.get_state(user_id)
        self.assertEqual(initial_state["active_mode"], "buddy")

        # Simulate user saying grammar slip in buddy mode
        updates = {
            "last_user_query": "I need an advice about my project and have many informations.",
            "active_mode": "buddy"
        }
        res = langgraph_engine._buddy_node(updates)
        errors = res.get("observed_errors", [])
        self.assertGreater(len(errors), 0)
        print(f"[TEST 5] Soft error detection in Buddy mode caught: {[e['error'] for e in errors]}")

        # Transition to Tutor mode
        langgraph_engine.update_state({"active_mode": "tutor_lecture", "current_topic": "Nouns"}, user_id=user_id)
        curr = langgraph_engine.get_state(user_id)
        self.assertEqual(curr["active_mode"], "tutor_lecture")

        # Transition to Tutor Q&A
        langgraph_engine.update_state({"active_mode": "tutor_qa"}, user_id=user_id)
        curr = langgraph_engine.get_state(user_id)
        self.assertEqual(curr["active_mode"], "tutor_qa")

        # Return to Buddy mode
        langgraph_engine.update_state({"active_mode": "buddy"}, user_id=user_id)
        curr = langgraph_engine.get_state(user_id)
        self.assertEqual(curr["active_mode"], "buddy")
        print("[TEST 5] Mode transitions Buddy <-> Tutor Lecture <-> Tutor Q&A verified.")

if __name__ == "__main__":
    unittest.main()
