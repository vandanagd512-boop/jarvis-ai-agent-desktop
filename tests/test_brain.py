"""Unit tests for JARVIS Brain, Reasoning Engine, and Offline Fallback."""

import unittest
from jarvis.brain.llm_provider import LLMResponse, ToolCall
from jarvis.brain.offline_provider import OfflineProvider
from jarvis.brain.prompt_templates import build_system_prompt
from jarvis.brain.router import ActionRouter
from jarvis.memory.conversation_store import conversation_store


class TestBrain(unittest.TestCase):
    """Test suite for reasoning engine, intent parser, prompt builder, and action router."""

    def setUp(self):
        self.offline_provider = OfflineProvider()
        self.router = ActionRouter()

    def test_offline_intent_recognition(self):
        """Verify regex and semantic parsing for system commands."""
        # 1. App Launch
        res = self.offline_provider.generate("open notepad")
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0].name, "launch_app")
        self.assertEqual(res.tool_calls[0].arguments["target"], "notepad")

        # 2. Battery status
        res_bat = self.offline_provider.generate("what is my battery level?")
        self.assertEqual(len(res_bat.tool_calls), 1)
        self.assertEqual(res_bat.tool_calls[0].name, "get_battery_status")

        # 3. Volume controls
        res_vol = self.offline_provider.generate("volume up please")
        self.assertEqual(len(res_vol.tool_calls), 1)
        self.assertEqual(res_vol.tool_calls[0].name, "volume_up")

        # 4. Greeting
        res_hello = self.offline_provider.generate("hello jarvis")
        self.assertEqual(len(res_hello.tool_calls), 0)
        self.assertIn("JARVIS is online", res_hello.content)

        # 5. WhatsApp Messaging
        res_wa = self.offline_provider.generate("text Alex on whatsapp: hello there")
        self.assertEqual(len(res_wa.tool_calls), 1)
        self.assertEqual(res_wa.tool_calls[0].name, "send_whatsapp_message")
        self.assertEqual(res_wa.tool_calls[0].arguments["recipient"], "alex")
        self.assertEqual(res_wa.tool_calls[0].arguments["message"], "hello there")

        # 6. Screenshot Capture
        res_shot = self.offline_provider.generate("take a screenshot")
        self.assertEqual(len(res_shot.tool_calls), 1)
        self.assertEqual(res_shot.tool_calls[0].name, "take_screenshot")

        # 7. Natural WhatsApp Command
        res_wa2 = self.offline_provider.generate("open whatsapp text mom hello")
        self.assertEqual(len(res_wa2.tool_calls), 1)
        self.assertEqual(res_wa2.tool_calls[0].name, "send_whatsapp_message")
        self.assertEqual(res_wa2.tool_calls[0].arguments["recipient"], "mom")
        self.assertEqual(res_wa2.tool_calls[0].arguments["message"], "hello")

        # 8. Location Detection
        res_loc = self.offline_provider.generate("Can you tell exact place of me?")
        self.assertEqual(len(res_loc.tool_calls), 1)
        self.assertEqual(res_loc.tool_calls[0].name, "get_current_location")

        # 9. YouTube Play
        res_yt = self.offline_provider.generate("open youtube and search lofi beats")
        self.assertEqual(len(res_yt.tool_calls), 1)
        self.assertEqual(res_yt.tool_calls[0].name, "play_youtube")

        # 10. Search Song
        res_song = self.offline_provider.generate("search song")
        self.assertEqual(len(res_song.tool_calls), 1)
        self.assertEqual(res_song.tool_calls[0].name, "play_youtube")

        # 11. WhatsApp Call
        res_call = self.offline_provider.generate("call someone")
        self.assertEqual(len(res_call.tool_calls), 1)
        self.assertEqual(res_call.tool_calls[0].name, "whatsapp_call")

        # 12. Chat Someone on WhatsApp
        res_chat = self.offline_provider.generate("chat someone")
        self.assertEqual(len(res_chat.tool_calls), 1)
        self.assertEqual(res_chat.tool_calls[0].name, "send_whatsapp_message")

        # 13. Laptop Charge Query
        res_charge = self.offline_provider.generate("what is current charge percent of my laptop")
        self.assertEqual(len(res_charge.tool_calls), 1)
        self.assertEqual(res_charge.tool_calls[0].name, "get_battery_status")

        # 14. Next Play on YouTube / Media
        res_next = self.offline_provider.generate("next play")
        self.assertEqual(len(res_next.tool_calls), 1)
        self.assertEqual(res_next.tool_calls[0].name, "media_next")

        # 15. Refresh Web Page
        res_ref = self.offline_provider.generate("refresh that page")
        self.assertEqual(len(res_ref.tool_calls), 1)
        self.assertEqual(res_ref.tool_calls[0].name, "refresh_page")

        # 16. Weather Query
        res_weather = self.offline_provider.generate("what is the weather in Tokyo")
        self.assertEqual(len(res_weather.tool_calls), 1)
        self.assertEqual(res_weather.tool_calls[0].name, "get_weather")
        self.assertEqual(res_weather.tool_calls[0].arguments["location"], "Tokyo")

        # 17. Wikipedia Query
        res_wiki = self.offline_provider.generate("search wikipedia for Quantum Computing")
        self.assertEqual(len(res_wiki.tool_calls), 1)
        self.assertEqual(res_wiki.tool_calls[0].name, "search_wikipedia")
        self.assertEqual(res_wiki.tool_calls[0].arguments["query"], "Quantum Computing")

        # 18. Git Status Query
        res_git = self.offline_provider.generate("check git status")
        self.assertEqual(len(res_git.tool_calls), 1)
        self.assertEqual(res_git.tool_calls[0].name, "get_git_status")

        # 19. Workflow Query
        res_wf = self.offline_provider.generate("run morning briefing")
        self.assertEqual(len(res_wf.tool_calls), 1)
        self.assertEqual(res_wf.tool_calls[0].name, "run_workflow")
        self.assertEqual(res_wf.tool_calls[0].arguments["workflow_id"], "morning_briefing")

        # 20. Clipboard Query
        res_clip = self.offline_provider.generate("what is on my clipboard")
        self.assertEqual(len(res_clip.tool_calls), 1)
        self.assertEqual(res_clip.tool_calls[0].name, "get_clipboard")

    def test_system_prompt_generation(self):
        """Verify dynamic system prompt compilation."""
        prompt = build_system_prompt(custom_instructions="Always answer in rhyme.")
        self.assertIn("JARVIS", prompt)
        self.assertIn("Operating System", prompt)
        self.assertIn("Always answer in rhyme", prompt)

    def test_action_router_execution(self):
        """Verify end-to-end query routing, tool dispatch, and conversation logging."""
        session_id = "test_brain_session"
        result = self.router.process_query("check ram memory usage", conversation_id=session_id)

        self.assertEqual(result["session_id"], session_id)
        self.assertTrue(len(result["actions_executed"]) > 0)
        self.assertEqual(result["actions_executed"][0]["action"], "get_memory_status")
        self.assertEqual(result["actions_executed"][0]["status"], "success")

        # Verify conversation store updated
        history = conversation_store.get_recent_messages(session_id)
        self.assertGreaterEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
