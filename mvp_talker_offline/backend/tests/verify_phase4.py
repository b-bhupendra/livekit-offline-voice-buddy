import os
import sys
import json
import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure backend directory is in python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import agent

class TestPhase4GenUIExpansion(unittest.TestCase):

    def test_01_versioned_genui_schema(self):
        """1. Verify that GenUI tools produce payloads with schema_version='1.0'."""
        captured_payloads = []

        async def fake_send_room_text(context, topic, payload_str):
            if topic == "genui":
                captured_payloads.append(json.loads(payload_str))

        with patch("agent.send_room_text", side_effect=fake_send_room_text):
            # Test trigger_quiz
            asyncio.run(agent.trigger_quiz(None, chapter=1, mode="milestone"))
            # Test dispute_answer
            asyncio.run(agent.dispute_answer(None, user_claim="I have went to the market"))
            # Test generate_revision_notes
            asyncio.run(agent.generate_revision_notes(None, chapter=1))
            # Test demonstrate_grammar_movement
            asyncio.run(agent.demonstrate_grammar_movement(None, title="Inversion Test"))

        self.assertEqual(len(captured_payloads), 4, "Expected 4 genui payloads to be broadcast")
        for p in captured_payloads:
            self.assertEqual(p.get("schema_version"), "1.0", f"Payload {p.get('component')} must have schema_version '1.0'")
            self.assertEqual(p.get("type"), "genui_render", "Payload must be type 'genui_render'")
            self.assertIn("component", p)
            self.assertIn("props", p)

        print(" [PASS] All GenUI events emit strict versioned schema (schema_version='1.0').")

    def test_02_demonstrate_grammar_movement_structure(self):
        """2. Verify demonstrate_grammar_movement syntactic tokens and return format."""
        captured_payloads = []

        async def fake_send_room_text(context, topic, payload_str):
            if topic == "genui":
                captured_payloads.append(json.loads(payload_str))

        with patch("agent.send_room_text", side_effect=fake_send_room_text):
            res_str = asyncio.run(agent.demonstrate_grammar_movement(
                None,
                title="Subject-Auxiliary Inversion",
                rule="Auxiliary verb moves before the subject.",
                chapter=2,
                initial_tokens=[
                    {"id": "tok-1", "text": "They", "role": "subject"},
                    {"id": "tok-2", "text": "have", "role": "aux"},
                    {"id": "tok-3", "text": "left", "role": "verb"}
                ],
                transformed_tokens=[
                    {"id": "tok-2", "text": "Have", "role": "aux"},
                    {"id": "tok-1", "text": "they", "role": "subject"},
                    {"id": "tok-3", "text": "left?", "role": "verb"}
                ],
                explanation="Auxiliary 'have' inverts with subject 'they'.",
                rule_citation="Oxford Guide Ch 2"
            ))

        res = json.loads(res_str)
        self.assertEqual(res.get("status"), "demonstration_rendered")
        self.assertEqual(res.get("chapter"), 2)

        self.assertEqual(len(captured_payloads), 1)
        movement_payload = captured_payloads[0]
        self.assertEqual(movement_payload.get("component"), "GrammarMovement")
        props = movement_payload.get("props", {})
        self.assertEqual(len(props.get("initial_tokens")), 3)
        self.assertEqual(len(props.get("transformed_tokens")), 3)
        self.assertEqual(props.get("transformed_tokens")[0]["role"], "aux")
        self.assertEqual(props.get("rule_citation"), "Oxford Guide Ch 2")

        print(" [PASS] demonstrate_grammar_movement correctly formats syntactic tokens and citations.")

    def test_03_in_process_tools_and_instructions_alignment(self):
        """3. Verify demonstrate_grammar_movement is registered in tools and guided in system prompt."""
        self.assertIn(agent.demonstrate_grammar_movement, agent.IN_PROCESS_TOOLS,
                      "demonstrate_grammar_movement must be in IN_PROCESS_TOOLS")
        self.assertIn("demonstrate_grammar_movement", agent.INSTRUCTIONS,
                      "System prompt INSTRUCTIONS must explicitly reference demonstrate_grammar_movement")
        self.assertIn("VISUAL SYNTACTIC MOVEMENT", agent.INSTRUCTIONS,
                      "System prompt INSTRUCTIONS must have a visual syntactic movement directive")
        print(" [PASS] Tool registered in IN_PROCESS_TOOLS and aligned with INSTRUCTIONS system prompt.")

    def test_04_frontend_design_tokens_and_components(self):
        """4. Verify frontend design tokens, Framer Motion component, and store methods exist."""
        fe_dir = os.path.join(BACKEND_DIR, "..", "VisualsFrontend")
        index_css_path = os.path.join(fe_dir, "src", "index.css")
        card_component_path = os.path.join(fe_dir, "src", "components", "InlineGrammarMovementCard.tsx")
        app_tsx_path = os.path.join(fe_dir, "src", "App.tsx")
        store_ts_path = os.path.join(fe_dir, "src", "store.ts")

        # 1. Check index.css for role tokens
        with open(index_css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        for token in ["--role-subject", "--role-aux", "--role-verb", "--role-object", "--role-particle"]:
            self.assertIn(token, css_content, f"Design token {token} must be defined in index.css")

        # 2. Check InlineGrammarMovementCard for layoutId
        self.assertTrue(os.path.exists(card_component_path), "InlineGrammarMovementCard.tsx must exist")
        with open(card_component_path, "r", encoding="utf-8") as f:
            card_content = f.read()
        self.assertIn("layoutId", card_content, "InlineGrammarMovementCard must utilize layoutId for Framer Motion tweening")

        # 3. Check App.tsx for movement item render
        with open(app_tsx_path, "r", encoding="utf-8") as f:
            app_content = f.read()
        self.assertIn("InlineGrammarMovementCard", app_content, "App.tsx must import and render InlineGrammarMovementCard")

        # 4. Check store.ts for pushInlineMovement filtering out streaming_card
        with open(store_ts_path, "r", encoding="utf-8") as f:
            store_content = f.read()
        self.assertIn("pushInlineMovement", store_content, "store.ts must define pushInlineMovement")
        self.assertIn("streaming_card", store_content, "store.ts pushInlineMovement must filter streaming_card")

        print(" [PASS] Frontend design tokens, Framer Motion layoutId card, and store integration verified.")

if __name__ == "__main__":
    unittest.main()
