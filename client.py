"""OpenAI-compatible completion and SSE clients for a self-hosted endpoint."""

from __future__ import annotations

import argparse
import json
import os
from urllib.request import Request, urlopen


def completions(endpoint: str, token: str, prompt: str, *, stream: bool = False, model: str = "Qwen/Qwen2.5-7B-Instruct"):
    if not token:
        raise ValueError("VLLM_API_KEY must be set")
    base = endpoint.rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": stream, "max_tokens": 128}
    request = Request(base + "/chat/completions", data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urlopen(request, timeout=120) as response:
        if not stream:
            yield json.load(response)["choices"][0]["message"]["content"]
            return
        for line in response:
            if not line.startswith(b"data:"):
                continue
            value = line[5:].strip()
            if value == b"[DONE]":
                return
            packet = json.loads(value)
            if packet.get("choices"):
                yield packet["choices"][0].get("delta", {}).get("content", "")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--endpoint", default=os.environ.get("VLLM_ENDPOINT", "http://127.0.0.1:8000"))
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()
    for chunk in completions(args.endpoint, os.environ.get("VLLM_API_KEY", ""), args.prompt, stream=args.stream):
        print(chunk, end="", flush=True)
    print()

