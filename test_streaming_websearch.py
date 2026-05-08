"""
Test: WebSearch streaming via Anthropic Messages API (/v1/messages)
Verifies that streaming + websearch_interception returns text_delta events.
"""
import anthropic
import time

client = anthropic.Anthropic(api_key="sk-1234", base_url="http://localhost:4002")

print("=== WebSearch Streaming Test ===")
print("Model: claude-sonnet-4-6 (bedrock/invoke)")
print()

start = time.time()
full_text = ""

with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "What is the latest Python version in 2026? One sentence answer."}],
    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 1}],
) as stream:
    for event in stream:
        if event.type == "content_block_delta" and event.delta.type == "text_delta":
            full_text += event.delta.text
            print(event.delta.text, end="", flush=True)

elapsed = time.time() - start
print(f"\n\n--- Result ---")
print(f"text_length={len(full_text)}, elapsed={elapsed:.1f}s")

if len(full_text) > 0:
    print("[PASS] ✅ Streaming websearch works")
else:
    print("[FAIL] ❌ text_length=0, streaming not working")
    exit(1)
