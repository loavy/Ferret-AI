import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, Response, jsonify, render_template, request, session, stream_with_context


app = Flask(__name__)
app.secret_key = os.getenv("FERRET_SECRET_KEY", "ferret_dev_secret_change_me")

API_URL = os.getenv("FERRET_API_URL", "http://localhost:11434/api/chat")
MODEL = os.getenv("FERRET_MODEL", "llama3.2")
MAX_LOG_CHARS = int(os.getenv("FERRET_MAX_LOG_CHARS", "12000"))
MAX_HISTORY_MESSAGES = int(os.getenv("FERRET_MAX_HISTORY_MESSAGES", "40"))


def get_log_directory() -> Path:
    configured = os.getenv("FERRET_LOG_DIR")
    if configured:
        log_dir = Path(configured).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    for base in (Path.home() / "OneDrive" / "Desktop", Path.home() / "Desktop"):
        if base.exists():
            log_dir = base / "logs_Ferret"
            log_dir.mkdir(parents=True, exist_ok=True)
            return log_dir

    log_dir = Path.home() / "logs_Ferret"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


LOG_DIR = get_log_directory()

DEFAULT_SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are Ferret AI, a local everyday assistant with a calm, thoughtful, polished conversational style. "
        "Feel like a smart friend who is useful for coding, writing, planning, studying, debugging, explaining, "
        "brainstorming, and small daily decisions. Be warm without being sugary, precise without sounding stiff, "
        "and honest when you are unsure. Default to English unless the user writes Portuguese, then answer in "
        "natural PT-BR. Keep answers lightweight: concise for simple asks, deeper only when the task needs it. "
        "For coding, give runnable code, exact commands, and practical tradeoffs. For non-coding, help clearly "
        "and conversationally. Ask one focused question when needed; otherwise make a reasonable assumption. "
        "Use Markdown code fences for code. Do not include Markdown images, GIFs, or fake links."
    ),
}

conversations_db = {}


def model_names_match(configured_model: str, installed_model: str) -> bool:
    configured = configured_model.lower().strip()
    installed = installed_model.lower().strip()
    return installed == configured or installed == f"{configured}:latest"


def new_history():
    return [DEFAULT_SYSTEM_MESSAGE.copy()]


def new_conversation(title="New chat", source="web"):
    now = datetime.now().isoformat(timespec="seconds")
    cid = str(uuid.uuid4())
    return {
        "id": cid,
        "title": title,
        "source": source,
        "created_at": now,
        "updated_at": now,
        "messages": new_history(),
    }


def ensure_conversation_store(sid: str):
    if sid not in conversations_db:
        conversation = new_conversation()
        conversations_db[sid] = {conversation["id"]: conversation}
        session["active_cid"] = conversation["id"]

    active_cid = session.get("active_cid")
    if active_cid not in conversations_db[sid]:
        session["active_cid"] = next(iter(conversations_db[sid]))


def current_conversation(sid: str):
    ensure_conversation_store(sid)
    return conversations_db[sid][session["active_cid"]]


def current_history(sid: str):
    return current_conversation(sid)["messages"]


def touch_conversation(conversation):
    conversation["updated_at"] = datetime.now().isoformat(timespec="seconds")


def maybe_title_from_user(conversation, user_text: str):
    if conversation["title"] != "New chat":
        return
    title = " ".join(user_text.split())[:48]
    conversation["title"] = title or "New chat"


def serialize_conversation(conversation):
    return {
        "id": conversation["id"],
        "title": conversation["title"],
        "source": conversation["source"],
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
    }


def serialize_messages(messages):
    return [message for message in messages if message.get("role") in {"user", "assistant"}]


def trim_history(messages):
    if len(messages) <= MAX_HISTORY_MESSAGES + 1:
        return messages
    return [messages[0], *messages[-MAX_HISTORY_MESSAGES:]]


def write_to_log(user_text: str, ai_text: str):
    file_path = LOG_DIR / f"chat_app_{datetime.now():%Y%m%d}.txt"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with file_path.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] USER: {user_text}\n")
        f.write(f"[{timestamp}] AI: {ai_text}\n")
        f.write("-" * 40 + "\n")


def read_log_file(filename: str):
    if not filename.endswith(".txt"):
        return None, "Only .txt files are allowed."

    safe_path = (LOG_DIR / filename).resolve()
    if not str(safe_path).startswith(str(LOG_DIR.resolve())):
        return None, "Invalid file path."
    if not safe_path.exists():
        return None, "Log file not found."

    try:
        return safe_path.read_text(encoding="utf-8"), None
    except OSError as exc:
        return None, str(exc)


def parse_log_messages(log_text: str):
    pattern = re.compile(
        r"(?ms)^\[[^\]]+\]\s+(USER|AI):\s*(.*?)(?=^\[[^\]]+\]\s+(?:USER|AI):|^-{3,}\s*$|\Z)"
    )
    messages = []
    for match in pattern.finditer(log_text):
        role = "user" if match.group(1) == "USER" else "assistant"
        content = match.group(2).strip()
        if content:
            messages.append({"role": role, "content": content})
    return messages


def history_from_imported_log(log_text: str):
    parsed_messages = parse_log_messages(log_text)
    if parsed_messages:
        return [DEFAULT_SYSTEM_MESSAGE.copy(), *parsed_messages[-MAX_HISTORY_MESSAGES:]]

    return [
        DEFAULT_SYSTEM_MESSAGE.copy(),
        {
            "role": "system",
            "content": (
                "The user imported an older Ferret conversation log. Use this as prior context "
                "for the next messages, but do not repeat it unless asked.\n\n"
                f"{log_text[-MAX_LOG_CHARS:]}"
            ),
        },
        {
            "role": "assistant",
            "content": "I imported that log and can continue from its context. What should we pick up?",
        },
    ]


@app.before_request
def ensure_session():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    ensure_conversation_store(session["sid"])


def stream_model(messages, timeout=60, save_to_session=False, sid=None, cid=None, user_input=None):
    @stream_with_context
    def generate():
        full_response = ""

        try:
            response = requests.post(
                API_URL,
                json={"model": MODEL, "messages": messages, "stream": True},
                stream=True,
                timeout=timeout,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    chunk = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                content = chunk.get("message", {}).get("content", "")
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'content': content})}\n\n"

                if chunk.get("done"):
                    break

            if save_to_session and sid and cid:
                conversation = conversations_db[sid][cid]
                history = conversation["messages"]
                history.append({"role": "assistant", "content": full_response})
                conversation["messages"] = trim_history(history)
                touch_conversation(conversation)
                write_to_log(user_input or "", full_response)

        except requests.exceptions.ConnectionError:
            yield f"data: {json.dumps({'error': 'Could not reach Ollama. Start it with `ollama serve` and make sure the model is pulled.'})}\n\n"
        except requests.exceptions.Timeout:
            yield f"data: {json.dumps({'error': 'The model took too long to answer. Try a shorter prompt or a smaller model.'})}\n\n"
        except requests.exceptions.RequestException as exc:
            yield f"data: {json.dumps({'error': f'Ollama request failed: {exc}'})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def handle_log_command(user_input: str, sid: str):
    parts = user_input.strip().split(maxsplit=1)

    if len(parts) == 1:
        logs = sorted((f.name for f in LOG_DIR.glob("*.txt")), reverse=True)
        if not logs:
            return jsonify({"type": "system", "content": "No log files found yet."})
        return jsonify({"type": "system", "content": "Available logs:\n" + "\n".join(logs)})

    log_content, error = read_log_file(parts[1])
    if error:
        return jsonify({"type": "system", "content": f"Error: {error}"})

    temp_messages = [
        *current_history(sid),
        {
            "role": "system",
            "content": (
                "Analyze this Ferret chat log. Summarize useful context, repeated issues, "
                "open coding tasks, and anything the user may want to continue today."
            ),
        },
        {"role": "user", "content": log_content[-MAX_LOG_CHARS:]},
    ]
    return stream_model(temp_messages, timeout=90)


@app.route("/")
def home():
    return render_template("index.html", model=MODEL)


@app.route("/conversations")
def conversations():
    sid = session["sid"]
    ensure_conversation_store(sid)
    items = sorted(
        conversations_db[sid].values(),
        key=lambda item: item["updated_at"],
        reverse=True,
    )
    active = current_conversation(sid)
    return jsonify({
        "active_id": active["id"],
        "conversations": [serialize_conversation(item) for item in items],
        "messages": serialize_messages(active["messages"]),
    })


@app.route("/conversations", methods=["POST"])
def create_conversation():
    sid = session["sid"]
    conversation = new_conversation()
    conversations_db[sid][conversation["id"]] = conversation
    session["active_cid"] = conversation["id"]
    return jsonify({
        "conversation": serialize_conversation(conversation),
        "messages": [],
    })


@app.route("/conversations/<cid>/activate", methods=["POST"])
def activate_conversation(cid):
    sid = session["sid"]
    if cid not in conversations_db[sid]:
        return jsonify({"error": "Conversation not found"}), 404
    session["active_cid"] = cid
    conversation = conversations_db[sid][cid]
    return jsonify({
        "conversation": serialize_conversation(conversation),
        "messages": serialize_messages(conversation["messages"]),
    })


@app.route("/conversations/<cid>", methods=["DELETE"])
def delete_conversation(cid):
    sid = session["sid"]
    if cid not in conversations_db[sid]:
        return jsonify({"error": "Conversation not found"}), 404

    del conversations_db[sid][cid]
    if not conversations_db[sid]:
        conversation = new_conversation()
        conversations_db[sid][conversation["id"]] = conversation
        session["active_cid"] = conversation["id"]
    elif session.get("active_cid") == cid:
        latest = max(conversations_db[sid].values(), key=lambda item: item["updated_at"])
        session["active_cid"] = latest["id"]

    active = current_conversation(sid)
    items = sorted(
        conversations_db[sid].values(),
        key=lambda item: item["updated_at"],
        reverse=True,
    )
    return jsonify({
        "active_id": active["id"],
        "conversations": [serialize_conversation(item) for item in items],
        "messages": serialize_messages(active["messages"]),
    })


@app.route("/conversations/import", methods=["POST"])
def import_conversation():
    sid = session["sid"]
    uploaded = request.files.get("log")
    if not uploaded:
        return jsonify({"error": "No log file uploaded"}), 400

    raw = uploaded.read()
    if len(raw) > MAX_LOG_CHARS * 3:
        raw = raw[-MAX_LOG_CHARS * 3:]

    try:
        log_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        log_text = raw.decode("utf-8", errors="replace")

    filename = Path(uploaded.filename or "imported-log.txt").name
    title = f"Imported {filename}"[:64]
    conversation = new_conversation(title=title, source="import")
    conversation["messages"] = history_from_imported_log(log_text)
    touch_conversation(conversation)
    conversations_db[sid][conversation["id"]] = conversation
    session["active_cid"] = conversation["id"]

    return jsonify({
        "conversation": serialize_conversation(conversation),
        "messages": serialize_messages(conversation["messages"]),
    })


@app.route("/status")
def status():
    try:
        response = requests.get(API_URL.replace("/api/chat", "/api/tags"), timeout=3)
        response.raise_for_status()
        models = [item.get("name", "") for item in response.json().get("models", [])]
        model_available = any(model_names_match(MODEL, model) for model in models)
        return jsonify({"online": True, "model": MODEL, "model_available": model_available})
    except requests.exceptions.RequestException:
        return jsonify({"online": False, "model": MODEL, "model_available": False})


@app.route("/clear", methods=["POST"])
def clear():
    conversation = current_conversation(session["sid"])
    conversation["messages"] = new_history()
    conversation["title"] = "New chat"
    touch_conversation(conversation)
    return jsonify({"ok": True, "message": "Fresh chat started."})


@app.route("/chat", methods=["POST"])
def chat():
    sid = session.get("sid")
    conversation = current_conversation(sid)
    cid = conversation["id"]
    user_input = (request.json or {}).get("message", "").strip()

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    lowered = user_input.lower()
    if lowered == "/clear":
        conversation["messages"] = new_history()
        conversation["title"] = "New chat"
        touch_conversation(conversation)
        return jsonify({"type": "system", "content": "Fresh chat started."})

    if lowered.startswith("/log"):
        return handle_log_command(user_input, sid)

    history = conversation["messages"]
    history.append({"role": "user", "content": user_input})
    conversation["messages"] = trim_history(history)
    maybe_title_from_user(conversation, user_input)
    touch_conversation(conversation)

    return stream_model(
        conversation["messages"],
        timeout=90,
        save_to_session=True,
        sid=sid,
        cid=cid,
        user_input=user_input,
    )


if __name__ == "__main__":
    print("\n" + "=" * 54)
    print(" Ferret AI Web is starting")
    print(f" Model: {MODEL}")
    print(f" Logs:  {LOG_DIR}")
    print(" Open:  http://127.0.0.1:5000")
    print("=" * 54 + "\n")
    app.run(port=5000, debug=True)
