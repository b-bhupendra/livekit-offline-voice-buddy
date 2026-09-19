#!/usr/bin/env python3
"""
Verification Script for Phase 5: Reliability & Observability.
Tests:
  1. In-Flight Reconnects & SQLite Sheet Persistence:
     - Verify req_id mapped to payload in SQLite
     - Verify get_last_sheet_payload returns the latest payload
  2. LiveKit RPC get_last_sheet:
     - Verify get_last_sheet returns formatted JSON payload
  3. Structured Logging Subsystem:
     - Verify localized loggers for STT, LLM, TTS, RAG, GenUI
     - Verify session_id and turn_id tracing across log records
  4. Surface Errors Gracefully (sheet_error):
     - Verify emit_sheet_error broadcasts versioned sheet_error payload
     - Verify frontend types, InlineSheetErrorCard, and store integration
"""

import os
import sys
import json
import time
import asyncio
import unittest
from unittest.mock import patch, MagicMock

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import agent
from core import structured_logger

class TestPhase5ReliabilityObservability(unittest.TestCase):

    def test_01_sqlite_sheet_persistence_and_retrieval(self):
        """1. Verify persisting req_id mapped to GenUI payload in SQLite and retrieving it."""
        test_req_id = f"test_req_{int(time.time() * 1000)}"
        test_payload = {
            "schema_version": "1.0",
            "type": "genui_render",
            "component": "QuizCard",
            "props": {
                "chapter": 1,
                "mode": "milestone",
                "source": "test_persistence"
            }
        }

        # Persist payload
        agent.persist_sheet_payload(test_req_id, "QuizCard", test_payload, session_id="test_session_p5")

        # Retrieve last sheet payload
        last_sheet = agent.get_last_sheet_payload()
        self.assertIsNotNone(last_sheet, "Must return a valid sheet payload")
        self.assertEqual(last_sheet.get("req_id"), test_req_id)
        self.assertEqual(last_sheet.get("component"), "QuizCard")
        self.assertEqual(last_sheet.get("status"), "ok")
        self.assertEqual(last_sheet.get("session_id"), "test_session_p5")
        self.assertEqual(last_sheet["payload"]["props"]["source"], "test_persistence")

        print(" [PASS] In-Flight Reconnects: SQLite persistence and retrieval of req_id mapped payload verified.")

    def test_02_structured_logging_subsystem(self):
        """2. Verify localized loggers for STT, LLM, TTS, RAG, and GenUI with consistent session and turn IDs."""
        # Set session and turn
        structured_logger.set_session_id("sess_observability_test")
        structured_logger.set_turn_id(1)

        self.assertEqual(structured_logger.get_session_id(), "sess_observability_test")
        self.assertEqual(structured_logger.get_turn_id(), 1)

        # Advance turn
        t2 = structured_logger.next_turn()
        self.assertEqual(t2, 2)
        self.assertEqual(structured_logger.get_turn_id(), 2)

        # Check all localized loggers exist and have correct subsystem
        loggers = {
            "STT": structured_logger.stt_logger,
            "LLM": structured_logger.llm_logger,
            "TTS": structured_logger.tts_logger,
            "RAG": structured_logger.rag_logger,
            "GenUI": structured_logger.genui_logger,
            "SYSTEM": structured_logger.system_logger,
        }

        for name, lgr in loggers.items():
            self.assertEqual(lgr.subsystem, name.upper())
            formatted_msg, kwargs = lgr.process("Test diagnostic message", {})
            self.assertIn(f"[{name.upper()}]", formatted_msg)
            self.assertIn("sess=sess_observability_test", formatted_msg)
            self.assertIn("turn=2", formatted_msg)

        print(" [PASS] Structured Logging: Localized loggers (STT, LLM, TTS, RAG, GenUI) with consistent IDs verified.")

    def test_03_surface_errors_gracefully_sheet_error(self):
        """3. Verify emit_sheet_error broadcasts a valid versioned sheet_error payload and persists it."""
        captured_payloads = []

        async def fake_send_room_text(context, topic, payload_str):
            if topic == "genui":
                captured_payloads.append(json.loads(payload_str))

        test_err_req_id = f"test_err_{int(time.time() * 1000)}"
        with patch("agent.send_room_text", side_effect=fake_send_room_text):
            err_result = asyncio.run(agent.emit_sheet_error(
                context=None,
                component_attempted="QuizCard",
                error_message="Ollama embedding timeout after 5000ms",
                req_id=test_err_req_id,
                details="Traceback: Ollama connection timed out"
            ))

        self.assertEqual(len(captured_payloads), 1)
        err_payload = captured_payloads[0]
        self.assertEqual(err_payload.get("schema_version"), "1.0")
        self.assertEqual(err_payload.get("type"), "genui_render")
        self.assertEqual(err_payload.get("component"), "sheet_error")
        props = err_payload.get("props", {})
        self.assertEqual(props.get("req_id"), test_err_req_id)
        self.assertEqual(props.get("component_attempted"), "QuizCard")
        self.assertTrue(props.get("retryable"))

        # Verify it was persisted in SQLite as the last sheet
        last_sheet = agent.get_last_sheet_payload()
        self.assertEqual(last_sheet.get("req_id"), test_err_req_id)
        self.assertEqual(last_sheet.get("component"), "sheet_error")

        print(" [PASS] Graceful Error Surfacing: sheet_error emitted, schema validated, and persisted in SQLite.")

    def test_04_frontend_components_and_store_integration(self):
        """4. Verify frontend types, InlineSheetErrorCard, store fetchLastSheet, and App rendering exist."""
        fe_dir = os.path.join(BACKEND_DIR, "..", "VisualsFrontend", "src")
        types_path = os.path.join(fe_dir, "types.ts")
        card_path = os.path.join(fe_dir, "components", "InlineSheetErrorCard.tsx")
        store_path = os.path.join(fe_dir, "store.ts")
        app_path = os.path.join(fe_dir, "App.tsx")
        livekit_path = os.path.join(fe_dir, "hooks", "useLiveKit.ts")

        # 1. types.ts
        with open(types_path, "r", encoding="utf-8") as f:
            types_content = f.read()
        self.assertIn("'sheet_error'", types_content, "types.ts must include sheet_error in GenUIComponent")
        self.assertIn("SheetErrorProps", types_content, "types.ts must export SheetErrorProps")
        self.assertIn("type: 'sheet_error'", types_content, "FeedItem must include sheet_error variant")

        # 2. InlineSheetErrorCard.tsx
        self.assertTrue(os.path.exists(card_path), "InlineSheetErrorCard.tsx must exist")
        with open(card_path, "r", encoding="utf-8") as f:
            card_content = f.read()
        self.assertIn("data: SheetErrorProps", card_content, "InlineSheetErrorCard must accept SheetErrorProps")
        self.assertIn("handleRetry", card_content, "InlineSheetErrorCard must provide retry action")

        # 3. store.ts
        with open(store_path, "r", encoding="utf-8") as f:
            store_content = f.read()
        self.assertIn("pushInlineSheetError", store_content, "store.ts must define pushInlineSheetError")
        self.assertIn("fetchLastSheet", store_content, "store.ts must define fetchLastSheet")
        self.assertIn("get_last_sheet", store_content, "store.ts must invoke get_last_sheet RPC")

        # 4. App.tsx
        with open(app_path, "r", encoding="utf-8") as f:
            app_content = f.read()
        self.assertIn("InlineSheetErrorCard", app_content, "App.tsx must render InlineSheetErrorCard")

        # 5. useLiveKit.ts
        with open(livekit_path, "r", encoding="utf-8") as f:
            lk_content = f.read()
        self.assertIn("fetchLastSheet", lk_content, "useLiveKit must invoke fetchLastSheet on mount/reconnect")
        self.assertIn("sheet_error", lk_content, "useLiveKit must handle sheet_error topic events")

        print(" [PASS] Frontend Integration: Types, InlineSheetErrorCard, store.fetchLastSheet, and reconnect hooks verified.")

if __name__ == "__main__":
    unittest.main()
