#!/usr/bin/env python3
"""
verify_curriculum_engine.py — Comprehensive Unit & Integration Tests
for Buddy Voice AI Curriculum Engine & Real-Time Audio Infrastructure.
"""

import os
import sys
import asyncio
import unittest
import sqlite3
from unittest.mock import MagicMock, patch

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from core.config import DATA_DIR, CURRICULUM_DB_PATH, LECTURE_AUDIO_DIR
from engines import curriculum_store
from tutor.curriculum_authoring import (
    CurriculumNode, CriticVerdict, parse_structured, structured_authoring_call
)
from tutor.curriculum_pipeline import pipeline, PipelineState
from core.gpu_arbiter import GPUSessionArbiter, gpu_arbiter
from tutor.curriculum_notify import (
    register_active_session, push_ready_event, flush_pending_announcements,
    queue_pending_announcement
)
from tutor.studio_tts import synthesize_studio_clip


class TestCurriculumEngine(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        curriculum_store.init_curriculum_db()
        curriculum_store.seed_canonical_nodes()

    def test_01_curriculum_store_tables_and_seed(self):
        """Verify 5 SQLite tables exist and canonical nodes are seeded."""
        conn = curriculum_store.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "curriculum_nodes", "curriculum_variants", "quiz_items",
            "reconsideration_requests", "critique_log"
        }
        self.assertTrue(expected.issubset(tables), f"Missing tables: {expected - tables}")

        # Check seeded node
        seeded = curriculum_store.get_node("ch1_concrete_abstract")
        self.assertIsNotNone(seeded)
        self.assertEqual(seeded["submodule"], "Concrete vs Abstract Nouns")
        self.assertEqual(seeded["canvas_type"], "classifier")

    def test_02_curriculum_variants_and_reconsideration(self):
        """Verify saving variants and logging/resolving reconsideration requests."""
        # 1. Log reconsideration request
        req_id = curriculum_store.log_reconsideration_request(
            node_id="ch1_concrete_abstract",
            style_hint="software_engineering",
            complaint="Explain like data structures"
        )
        self.assertTrue(req_id.startswith("recons_"))

        # 2. Save variant
        variant_draft = {
            "spoken_summary": "Nouns are like variable identifiers and schemas.",
            "canvas_type": "matrix",
            "canvas_config": {"columns": ["Static", "Dynamic"]},
            "lecture_paragraphs": ["In OOP, classes represent categories..."],
            "citations": ["Oxford Guide p. 12"]
        }
        var_id = curriculum_store.save_variant("ch1_concrete_abstract", "software_engineering", variant_draft)
        self.assertIsNotNone(var_id)

        # 3. Retrieve variant
        loaded = curriculum_store.get_variant("ch1_concrete_abstract", "software_engineering")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["lecture_paragraphs"], variant_draft["lecture_paragraphs"])

        # 4. Resolve reconsideration request
        curriculum_store.resolve_reconsideration_request(req_id, var_id)

        # 5. Clustered requests check
        clusters = curriculum_store.get_clustered_reconsideration_nodes(min_count=1)
        self.assertTrue(any(node == "ch1_concrete_abstract" for node, _ in clusters))

    def test_03_authoring_pydantic_validation(self):
        """Verify CurriculumNode schema validation and repair fallback."""
        raw_json = """{
            "node_id": "test_concord",
            "submodule": "Subject-Verb Agreement",
            "title": "Subject-Verb Concord Masterclass",
            "core_concept": "Subjects and verbs must agree in number.",
            "canvas_type": "classifier",
            "canvas_config": {"left": "Singular Subject", "right": "Singular Verb"},
            "lecture_paragraphs": ["Paragraph 1 explaining concord.", "Paragraph 2 with examples."],
            "citations": ["Oxford Guide section 14"]
        }"""
        parsed = parse_structured(raw_json, CurriculumNode)
        self.assertIsInstance(parsed, CurriculumNode)
        self.assertEqual(parsed.canvas_type, "classifier")
        self.assertEqual(parsed.title, "Subject-Verb Concord Masterclass")

    async def test_04_gpu_arbiter_concurrency_gate(self):
        """Verify GPUSessionArbiter pauses background tasks while voice is active."""
        arbiter = GPUSessionArbiter()
        self.assertTrue(arbiter.is_idle)

        # Set voice active (call in progress)
        arbiter.set_voice_active(True)
        self.assertFalse(arbiter.is_idle)

        flag = []
        async def background_task():
            await arbiter.wait_for_idle()
            flag.append("executed")

        task = asyncio.create_task(background_task())
        # Should NOT execute immediately because voice is active
        await asyncio.sleep(0.01)
        self.assertEqual(flag, [])

        # Turn voice off
        arbiter.set_voice_active(False)
        await asyncio.sleep(0.05)
        self.assertEqual(flag, ["executed"])

    async def test_05_curriculum_notify_context_injection(self):
        """Verify push_ready_event updates LLM session.history to eliminate Context Blindness."""
        mock_session = MagicMock()
        mock_session.history = MagicMock()
        mock_session.agent_state = "speaking"
        mock_session.room_io = MagicMock()
        mock_session.room_io.room = MagicMock()
        mock_session.room_io.room.local_participant = MagicMock()
        mock_session.room_io.room.local_participant.publish_data = MagicMock(return_value=asyncio.sleep(0))

        register_active_session(mock_session)

        state = {
            "node_id": "ch1_concrete_abstract",
            "job_type": "build",
            "chapter_idx": 1,
            "draft": {
                "title": "Nouns & Classification",
                "core_concept": "Mass uncountable nouns take singular determiners.",
                "canvas_type": "classifier",
                "canvas_config": {},
                "lecture_paragraphs": ["Test paragraph"],
                "citations": ["Oxford Guide"]
            }
        }
        await push_ready_event(state)

        # Check session.history.add_message was called with system role
        mock_session.history.add_message.assert_called_once()
        args, kwargs = mock_session.history.add_message.call_args
        self.assertEqual(kwargs.get("role"), "system")
        self.assertIn("Nouns & Classification", kwargs.get("content", ""))

        # Because agent_state was 'speaking', announcement should be in pending queue
        pending = flush_pending_announcements()
        self.assertIsNotNone(pending)
        self.assertEqual(pending["node_id"], "ch1_concrete_abstract")

    async def test_06_studio_tts_generation(self):
        """Verify studio TTS generates valid WAV clip to LECTURE_AUDIO_DIR."""
        out_id = "test_clip_001"
        out_path = await synthesize_studio_clip("Welcome to English Grammar Mastery with Buddy.", out_id)
        self.assertTrue(os.path.exists(out_path))
        self.assertTrue(out_path.endswith(".wav"))
        self.assertGreater(os.path.getsize(out_path), 1000)

    def test_07_langgraph_pipeline_structure(self):
        """Verify compiled LangGraph pipeline graph contains all 8 required nodes."""
        nodes = pipeline.nodes
        expected_nodes = {
            "retrieve_context", "draft_content", "deterministic_gate",
            "semantic_critic", "persist", "render_audio",
            "notify", "flag_and_stop"
        }
        self.assertTrue(expected_nodes.issubset(set(nodes.keys())), f"Missing nodes: {expected_nodes - set(nodes.keys())}")

    def test_08_zero_tool_fast_path(self):
        """Verify Zero-Tool Fast Path default and dynamic mounting/unmounting."""
        from agent import BUDDY_FAST_PATH_TOOLS, TUTOR_MODE_TOOLS, mount_tutor_tools, unmount_tools_to_fastpath
        self.assertEqual(len(BUDDY_FAST_PATH_TOOLS), 0, "Buddy fast path must start with 0 tools")
        self.assertGreaterEqual(len(TUTOR_MODE_TOOLS), 20, "Tutor mode must hold full toolset")

        # Test mock session mounting
        class MockSession:
            def __init__(self):
                self._tools = []
            @property
            def tools(self):
                return self._tools

        mock_sess = MockSession()
        self.assertEqual(len(mock_sess.tools), 0)
        mount_tutor_tools(mock_sess)
        self.assertEqual(len(mock_sess.tools), len(TUTOR_MODE_TOOLS))
        unmount_tools_to_fastpath(mock_sess)
        self.assertEqual(len(mock_sess.tools), 0)

    def test_09_autonomous_crawler_and_canvas_html(self):
        """Verify AutonomousCurriculumCrawler topic discovery and canvas_html in schema."""
        from tutor.curriculum_crawler import get_crawler
        from tutor.curriculum_authoring import CurriculumNode
        crawler = get_crawler()
        topics = crawler.discover_topics(chapter_filter=1)
        self.assertIsInstance(topics, list)

        # Verify CurriculumNode schema accepts canvas_html
        node = CurriculumNode(
            node_id="test_node_universal",
            chapter_idx=1,
            submodule="Test Universal Submodule",
            title="Test Universal Diagram",
            core_concept="Test concept",
            lecture_paragraphs=["Paragraph 1", "Paragraph 2"],
            canvas_type="universal_sandbox",
            canvas_html="<div class='p-4 bg-slate-900 text-white'>Interactive SVG Model</div>",
            citations=["Oxford Guide"]
        )
        self.assertIn("Interactive SVG Model", node.canvas_html)
        self.assertEqual(node.canvas_type, "universal_sandbox")

    async def test_10_dynamic_scenario_prompt_injection(self):
        """Verify start_dynamic_scenario queries RAG and injects persona prompt into AgentSession."""
        from engines.simulation_engine import SimulationEngine
        sim = SimulationEngine()
        
        class MockAgent:
            def __init__(self):
                self.instructions = ""

        class MockSession:
            def __init__(self):
                self.agent = MockAgent()
                self.tools = []
            def update_agent(self, new_agent):
                self.agent = new_agent

        sess = MockSession()
        res = await sim.start_dynamic_scenario(sess, "negotiating flat maintenance with landlady", chapter_idx=3)
        self.assertIn("Scenario started", res)
        self.assertIn("LIVE, INTERACTIVE SCENARIO SIMULATION", sess.agent.instructions.upper())
        self.assertIn("COMMUNICATIVE FRICTION", sess.agent.instructions.upper())


if __name__ == "__main__":
    unittest.main(verbosity=2)
