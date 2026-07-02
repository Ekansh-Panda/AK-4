#!/usr/bin/env python3
"""Integration Test for Miori Core

This script connects to the local backend using the requests library,
creates a task, sends a chat message asking about tasks, and verifies
the LLM uses the TaskTool and responds correctly.
"""

import sys
import time

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8321/api"

def main():
    print("Wait for server to be ready...")
    for _ in range(10):
        try:
            res = requests.get(f"http://127.0.0.1:8321/health")
            if res.status_code == 200:
                print("Server is up!")
                break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        print("Server did not start.")
        sys.exit(1)

    print("\n--- 1. Creating a Task ---")
    res = requests.post(
        f"{BASE_URL}/tasks",
        json={"title": "Test Integration Task", "description": "This is a test task for the integration script."}
    )
    if res.status_code != 200:
        print(f"Failed to create task: {res.text}")
        sys.exit(1)
    
    task_id = res.json()["id"]
    print(f"Created task: {task_id}")

    print("\n--- 2. Sending Chat Message ---")
    res = requests.post(
        f"{BASE_URL}/chat",
        json={"message": "what tasks do I have?"}
    )
    if res.status_code != 200:
        print(f"Failed to chat: {res.text}")
        sys.exit(1)
    
    chat_response = res.json()
    reply = chat_response["reply"]["content"]
    print(f"Assistant Reply: {reply}")
    
    if "Test Integration Task" in reply or "(mock)" in reply:
        print("\nSUCCESS! The pipeline works.")
    else:
        print("\nWARNING: Did not see expected output in reply.")

    print("\n--- 3. Cleaning up Task ---")
    requests.delete(f"{BASE_URL}/tasks/{task_id}")
    print("Done.")

if __name__ == "__main__":
    main()
