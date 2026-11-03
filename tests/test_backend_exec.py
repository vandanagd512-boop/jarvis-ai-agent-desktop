import os
import sys
sys.path.insert(0, os.path.abspath("."))
from jarvis.brain.router import action_router

def run_tests():
    queries = [
        "Jarvis volume of",
        "call alex on whatsapp",
        "call unknown_person on whatsapp",
        "take a screenshot",
        "jarvis search Wikipedia for program computer"
    ]
    for q in queries:
        print(f"\n--- TESTING QUERY: {q} ---")
        res = action_router.process_query(q)
        print("RESPONSE:", res.get("response"))
        print("ACTIONS:", res.get("actions_executed"))
        print("PROVIDER:", res.get("provider_used"))

if __name__ == "__main__":
    run_tests()
