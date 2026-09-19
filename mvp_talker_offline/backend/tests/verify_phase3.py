import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is in python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import agent
from livekit.agents import stt

class TestPhase3RealTimeResponsiveness(unittest.TestCase):

    def test_01_faster_whisper_streaming_capabilities(self):
        """1. Verify FasterWhisperSTT capabilities are set to streaming=True and interim_results=True."""
        stt_instance = agent.FasterWhisperSTT(model_size="tiny.en")
        self.assertTrue(stt_instance.capabilities.streaming, "FasterWhisperSTT must have streaming=True")
        self.assertTrue(stt_instance.capabilities.interim_results, "FasterWhisperSTT must have interim_results=True")
        print(" [PASS] FasterWhisperSTT configured for streaming and interim results.")

    def test_02_streaming_adapter(self):
        """2. Verify StreamingFasterWhisperAdapter initializes correctly."""
        stt_instance = agent.FasterWhisperSTT(model_size="tiny.en")
        vad_instance = MagicMock()
        adapter = agent.StreamingFasterWhisperAdapter(stt_instance, vad_instance)
        self.assertIsInstance(adapter, stt.StreamAdapter, "Adapter must subclass stt.StreamAdapter")
        self.assertTrue(adapter.capabilities.interim_results, "Adapter must have interim_results=True")
        print(" [PASS] StreamingFasterWhisperAdapter correctly implemented.")

    def test_03_voice_priority_manager(self):
        """3. Verify VoiceTurnPriorityManager accurately tracks state and provides async context lock."""
        manager = agent.VoiceTurnPriorityManager()
        self.assertFalse(manager.is_voice_active)
        
        manager.user_speaking = True
        self.assertTrue(manager.is_voice_active, "Manager should be active when user is speaking")
        
        manager.user_speaking = False
        manager.agent_state = "speaking"
        self.assertTrue(manager.is_voice_active, "Manager should be active when agent is speaking")
        
        manager.agent_state = "thinking"
        self.assertTrue(manager.is_voice_active, "Manager should be active when agent is thinking")
        
        manager.agent_state = "listening"
        self.assertFalse(manager.is_voice_active, "Manager should be inactive when agent is listening and user is quiet")
        print(" [PASS] VoiceTurnPriorityManager correctly tracks voice activity priority.")

if __name__ == "__main__":
    unittest.main()
