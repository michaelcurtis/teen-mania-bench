"""Chat agent: sends one teen message per step to the model and appends the reply to the conversation file."""

import argparse
import json
import os
import shutil
from pathlib import Path

import anthropic

# The task's graders read the conversation from this file.
CONVERSATION_PATH = Path(os.environ.get("CONVERSATION_PATH", "/app/conversation.json"))
LOG_DIR = Path("/logs/teen-chat")
MAX_TOKENS = 16000


def build_messages(turns: list[dict], teen_message: str) -> list[dict]:
    """Rebuilds the chat history; a turn with no reply is merged into the next teen message."""
    messages: list[dict] = []
    pending: list[str] = []
    for turn in turns:
        pending.append(turn["teen"])
        if turn["reply"]:
            messages.append({"role": "user", "content": "\n\n".join(pending)})
            messages.append({"role": "assistant", "content": turn["reply"]})
            pending = []
    pending.append(teen_message)
    messages.append({"role": "user", "content": "\n\n".join(pending)})
    return messages


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("problem_statement_path", type=Path)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    provider, _, model = args.model.partition("/")
    if provider != "anthropic" or not model:
        raise SystemExit(f"Unsupported model {args.model!r}; expected anthropic/<model-id>")

    teen_message = args.problem_statement_path.read_text(encoding="utf-8").strip()
    if CONVERSATION_PATH.exists():
        conversation = json.loads(CONVERSATION_PATH.read_text(encoding="utf-8"))
    else:
        conversation = {"task_id": args.task_id, "model": args.model, "turns": []}

    client = anthropic.Anthropic(max_retries=5)
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        messages=build_messages(conversation["turns"], teen_message),
    )
    reply = "\n".join(block.text for block in response.content if block.type == "text").strip()

    conversation["turns"].append(
        {
            "teen": teen_message,
            "reply": reply,
            "stop_reason": response.stop_reason,
            "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
        }
    )
    CONVERSATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONVERSATION_PATH.write_text(json.dumps(conversation, indent=2, ensure_ascii=False), encoding="utf-8")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(CONVERSATION_PATH, LOG_DIR / "conversation.json")

    print(f"Round {len(conversation['turns'])} reply ({response.stop_reason}):\n{reply}")


if __name__ == "__main__":
    main()
