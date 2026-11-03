import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

print("Step 1: start", flush=True)

from jarvis.core.config import Settings
print("Step 2: imported Settings", flush=True)

from jarvis.core.events import Event, EventBus, EventType
print("Step 3: imported Events", flush=True)

from jarvis.core.context import SystemContext
print("Step 4: imported SystemContext", flush=True)

from tests.test_core import TestCore
print("Step 5: imported TestCore", flush=True)

from tests.test_memory import TestMemory
print("Step 5b: imported TestMemory", flush=True)

from tests.test_automations import TestAutomations
print("Step 5c: imported TestAutomations", flush=True)

from tests.test_brain import TestBrain
print("Step 5d: imported TestBrain", flush=True)

from tests.test_voice import TestVoice
print("Step 5e: imported TestVoice", flush=True)

from tests.test_productivity_tools import TestProductivityTools
print("Step 5f: imported TestProductivityTools", flush=True)

from tests.test_vision_and_controls import TestVisionAndControls
print("Step 5g: imported TestVisionAndControls", flush=True)

from tests.test_plugins_and_workflows import TestPluginsAndWorkflows
print("Step 5h: imported TestPluginsAndWorkflows", flush=True)

from tests.test_ui_and_api import TestUiAndApi
print("Step 5i: imported TestUiAndApi", flush=True)

tc = TestCore()
print("Step 6: running test_settings_initialization", flush=True)
tc.test_settings_initialization()
print("Step 7: test_settings_initialization passed", flush=True)

print("Step 8: running test_exception_hierarchy", flush=True)
tc.test_exception_hierarchy()
print("Step 9: test_exception_hierarchy passed", flush=True)

print("Step 10: running test_system_context", flush=True)
tc.test_system_context()
print("Step 11: test_system_context passed", flush=True)

print("Step 12: running test_event_bus_publish_subscribe", flush=True)
tc.test_event_bus_publish_subscribe()
print("Step 13: test_event_bus_publish_subscribe passed", flush=True)

print("Step 14: running TestMemory", flush=True)
tm = TestMemory()
TestMemory.setUpClass()
try:
    tm.test_estimate_tokens()
    print("Step 15: test_estimate_tokens passed", flush=True)
    tm.test_conversation_and_messages()
    print("Step 16: test_conversation_and_messages passed", flush=True)
    tm.test_semantic_facts_and_search()
    print("Step 17: test_semantic_facts_and_search passed", flush=True)
    tm.test_notes_and_reminders()
    print("Step 18: test_notes_and_reminders passed", flush=True)
finally:
    TestMemory.tearDownClass()

print("Step 19: running TestAutomations", flush=True)
ta = TestAutomations()
ta.test_memory_metrics()
print("Step 20: test_memory_metrics passed", flush=True)
ta.test_disk_metrics()
print("Step 21: test_disk_metrics passed", flush=True)
ta.test_battery_and_uptime()
print("Step 22: test_battery_and_uptime passed", flush=True)
ta.test_window_manager_enumeration()
print("Step 23: test_window_manager_enumeration passed", flush=True)
ta.test_app_launcher_known_apps()
print("Step 24: test_app_launcher_known_apps passed", flush=True)

print("Step 25: running TestBrain", flush=True)
tb = TestBrain()
tb.setUp()
tb.test_offline_intent_recognition()
print("Step 26: test_offline_intent_recognition passed", flush=True)
tb.test_system_prompt_generation()
print("Step 27: test_system_prompt_generation passed", flush=True)
tb.test_action_router_execution()
print("Step 28: test_action_router_execution passed", flush=True)

print("Step 29: running TestVoice", flush=True)
tv = TestVoice()
tv.setUp()
tv.test_wake_word_detection()
print("Step 30: test_wake_word_detection passed", flush=True)
tv.test_voice_listener_state_transitions()
print("Step 31: test_voice_listener_state_transitions passed", flush=True)
tv.test_tts_properties()
print("Step 32: test_tts_properties passed", flush=True)

print("Step 33: running TestProductivityTools", flush=True)
tpt = TestProductivityTools()
tpt.test_file_operations()
print("Step 34: test_file_operations passed", flush=True)
tpt.test_calendar_natural_date_parsing()
print("Step 35: test_calendar_natural_date_parsing passed", flush=True)
tpt.test_code_runner_execution()
print("Step 36: test_code_runner_execution passed", flush=True)

print("Step 37: running TestVisionAndControls", flush=True)
tvc = TestVisionAndControls()
tvc.test_screen_capture_and_encoding()
print("Step 38: test_screen_capture_and_encoding passed", flush=True)
tvc.test_ocr_engine_processing()
print("Step 39: test_ocr_engine_processing passed", flush=True)
tvc.test_clipboard_manager_history()
print("Step 40: test_clipboard_manager_history passed", flush=True)

print("Step 41: running TestPluginsAndWorkflows", flush=True)
tpw = TestPluginsAndWorkflows()
tpw.test_plugin_discovery_and_execution()
print("Step 42: test_plugin_discovery_and_execution passed", flush=True)
tpw.test_workflow_orchestration()
print("Step 43: test_workflow_orchestration passed", flush=True)

print("Step 44: running TestUiAndApi", flush=True)
tua = TestUiAndApi()
tua.test_dashboard_index()
print("Step 44b: test_dashboard_index passed", flush=True)
tua.test_health_check_endpoint()
print("Step 45: test_health_check_endpoint passed", flush=True)
tua.test_status_endpoint()
print("Step 46: test_status_endpoint passed", flush=True)
tua.test_query_endpoint()
print("Step 47: test_query_endpoint passed", flush=True)
tua.test_workflows_endpoint()
print("Step 48: test_workflows_endpoint passed", flush=True)
tua.test_screenshot_and_vision_endpoints()
print("Step 49: test_screenshot_and_vision_endpoints passed", flush=True)

print("ALL TESTS PASSED SUCCESSFULLY!", flush=True)
