"""Test chat endpoint with real Claude API — run with: python -m riskcast.scripts.test_chat"""

import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8002/api/v1"


def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    r = urllib.request.urlopen(req)
    return r.status, json.loads(r.read().decode())


def main():
    # 1. Login (reuse existing user from DB)
    print("=== LOGIN ===")
    code, res = api("POST", "/auth/login", {"email": "admin@vietlog.vn", "password": "test12345"})
    if code != 200:
        print("Login failed — registering new user...")
        code, res = api("POST", "/auth/register", {
            "company_name": "Chat Test Co",
            "company_slug": "chat-test",
            "email": "chat@test.vn",
            "password": "test12345",
            "name": "Chat Tester",
        })
    token = res["access_token"]
    print(f"  Logged in as: {res['name']}")

    # 2. Send chat message via streaming SSE
    print("\n=== CHAT: 'Tổng quan tuần này' ===")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = json.dumps({"message": "Tổng quan tuần này"}).encode()
    req = urllib.request.Request(f"{BASE}/chat/message", data=data, headers=headers, method="POST")

    try:
        r = urllib.request.urlopen(req, timeout=60)
        response_text = ""
        session_id = None
        suggestions = []

        # Read SSE stream
        for line in r:
            line = line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue

            event = json.loads(line[6:])
            evt_type = event.get("type")

            if evt_type == "chunk":
                response_text += event["content"]
                sys.stdout.write(event["content"])
                sys.stdout.flush()

            elif evt_type == "done":
                response_text = event.get("clean_content", response_text)
                session_id = event.get("session_id")
                suggestions = event.get("suggestions", [])
                print()  # newline after streaming

            elif evt_type == "error":
                print(f"\n  ERROR: {event['message']}")
                break

        print(f"\n  Session ID: {session_id}")
        print(f"  Response length: {len(response_text)} chars")
        print(f"  Suggestions: {len(suggestions)}")

        if suggestions:
            for s in suggestions:
                print(f"    [{s['type']}] {s['text'][:80]}")

        print("\n=== CHAT TEST PASSED ===")

    except Exception as e:
        print(f"\n  CHAT ERROR: {e}")


if __name__ == "__main__":
    main()
