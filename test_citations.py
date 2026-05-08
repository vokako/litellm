"""
Test: Citations via LangChain ChatOpenAI -> LiteLLM -> Bedrock Invoke
Verifies that document blocks with citations enabled return citation data.
"""
import asyncio
import json
from typing import Optional

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI


class CitationCapturingChatOpenAI(ChatOpenAI):
    def _convert_chunk_to_generation_chunk(
        self, chunk: dict, default_chunk_class: type, base_generation_info: Optional[dict]
    ) -> Optional[ChatGenerationChunk]:
        gen_chunk = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        if gen_chunk is None:
            return None
        choices = chunk.get("choices") or []
        if not choices:
            return gen_chunk
        delta = choices[0].get("delta") or {}
        psf = delta.get("provider_specific_fields") or {}
        citation = psf.get("citation")
        if citation and isinstance(gen_chunk.message, AIMessageChunk):
            gen_chunk.message.additional_kwargs.setdefault("citations_raw", []).append(citation)
        return gen_chunk


DOCS = [
    {"title": "France Facts", "content": "The capital of France is Paris. The Eiffel Tower is 330 meters tall."},
    {"title": "Germany Facts", "content": "The capital of Germany is Berlin. The Brandenburg Gate was built in 1791."},
]


async def main():
    print("=== Citations Test ===")
    print("Model: claude-sonnet-4-6 (bedrock/invoke)")
    print()

    llm = CitationCapturingChatOpenAI(
        api_key="sk-1234",
        base_url="http://localhost:4002/v1",
        model_name="claude-sonnet-4-6",
        streaming=True,
        temperature=0,
    )

    blocks = []
    for doc in DOCS:
        blocks.append({
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": doc["content"]},
            "title": doc["title"],
            "citations": {"enabled": True},
        })
    blocks.append({"type": "text", "text": "How tall is the Eiffel Tower? Cite the source."})

    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content=blocks),
    ]

    gathered = None
    async for chunk in llm.astream(messages):
        gathered = chunk if gathered is None else gathered + chunk

    final_ak = getattr(gathered, "additional_kwargs", None) or {}
    citations_raw = final_ak.get("citations_raw")

    print(f"Response: {gathered.content[:200]}")
    print()

    if citations_raw:
        print(f"citations_raw count: {len(citations_raw)}")
        print(json.dumps(citations_raw[0], indent=2))
        print(f"\n[PASS] ✅ Citations working")
    else:
        print("citations_raw: MISSING")
        print(f"\n[FAIL] ❌ No citations returned")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
