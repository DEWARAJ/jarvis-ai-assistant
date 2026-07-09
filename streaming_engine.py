"""
streaming_engine.py  —  JARVIS v7.0
Anthropic streaming API. First tokens in ~300ms.
TTS starts on sentence 1 while sentence 2 is still generating.
"""
from __future__ import annotations
import os, re, queue

try:
    import anthropic as _ant; _ANT_OK = True
except ImportError:
    _ant = None; _ANT_OK = False

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError:
    pass

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def stream_response(
    user_message: str,
    system_prompt: str,
    history: list[dict],
    tts_queue: queue.Queue,
    print_live: bool = True,
) -> str:
    """
    Stream Claude response token-by-token.
    Complete sentences pushed to tts_queue for immediate TTS.
    Returns full response string.
    """
    if not _ANT_OK:
        return "[streaming] anthropic not installed."
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        return "[streaming] ANTHROPIC_API_KEY not set."

    client   = _ant.Anthropic(api_key=key)
    messages = list(history) + [{"role": "user", "content": user_message}]
    full     = ""
    pending  = ""

    try:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for chunk in stream.text_stream:
                full    += chunk
                pending += chunk
                if print_live:
                    print(chunk, end="", flush=True)
                parts = _SENTENCE_END.split(pending)
                for sentence in parts[:-1]:
                    s = sentence.strip()
                    if len(s) > 8:
                        tts_queue.put(s)
                pending = parts[-1]

        if pending.strip() and len(pending.strip()) > 5:
            tts_queue.put(pending.strip())
        if print_live:
            print()

    except Exception as e:
        msg = f"[streaming error] {type(e).__name__}: {e}"
        print(f"\n{msg}")
        return msg

    return full
