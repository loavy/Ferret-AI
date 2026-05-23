import os
from pathlib import Path


def default_log_dir():
    configured = os.getenv("FERRET_LOG_DIR")
    if configured:
        return Path(configured).expanduser()

    for path in (Path.home() / "OneDrive" / "Desktop", Path.home() / "Desktop"):
        if path.exists():
            return path / "logs_Ferret"
    return Path.home() / "logs_Ferret"


BASE_COMPANION_PROMPT = (
    "You are Ferret AI, a local everyday assistant with a calm, thoughtful, polished conversational style. "
    "Feel like a smart friend who is useful for coding, writing, planning, studying, debugging, explaining, "
    "brainstorming, and small daily decisions. Be warm without being sugary, precise without sounding stiff, "
    "and honest when you are unsure. Default to English unless the user writes Portuguese, then answer in "
    "natural PT-BR. Keep answers lightweight: concise for simple asks, deeper only when the task needs it. "
    "For coding, give runnable code, exact commands, and practical tradeoffs. For non-coding, help clearly "
    "and conversationally. Ask one focused question when needed; otherwise make a reasonable assumption. "
    "Use Markdown code fences for code. Do not include Markdown images, GIFs, or fake links."
)


CONFIG = {
    "url": os.getenv("FERRET_API_URL", "http://localhost:11434/api/chat"),
    "model": os.getenv("FERRET_MODEL", "llama3.2"),
    "log_dir": default_log_dir(),
    "persona": BASE_COMPANION_PROMPT,
    "max_context_messages": int(os.getenv("FERRET_MAX_CONTEXT_MESSAGES", "80")),
    "typing_speed": float(os.getenv("FERRET_TYPING_SPEED", "0.003")),
    "max_code_lines": 20,
    "max_file_chars": int(os.getenv("FERRET_MAX_FILE_CHARS", "18000")),
}


PERSONAS = {
    "friend": (
        BASE_COMPANION_PROMPT
        + " Be conversational and steady. Make the user feel like returning to you every day is easy."
    ),
    "thinker": (
        BASE_COMPANION_PROMPT
        + " Think carefully and explain the shape of the answer with calm, concise reasoning."
    ),
    "writer": (
        BASE_COMPANION_PROMPT
        + " Help with wording, tone, structure, translation, and clearer everyday communication."
    ),
    "reviewer": (
        BASE_COMPANION_PROMPT
        + " Use a code-review stance: lead with bugs, risks, regressions, and missing tests before style notes."
    ),
    "debugger": (
        BASE_COMPANION_PROMPT
        + " Debug methodically. Ask for missing traceback details only when they are truly needed."
    ),
    "concise": (
        BASE_COMPANION_PROMPT
        + " Keep answers short. Prefer bullets, commands, and code over long explanation."
    ),
}


C = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "brand": "\033[38;5;215m",
    "brand_alt": "\033[38;5;210m",
    "prompt": "\033[38;5;117m",
    "context": "\033[38;5;180m",
    "ai": "\033[38;5;223m",
    "ai_alt": "\033[38;5;229m",
    "code": "\033[38;5;116m",
    "code_border": "\033[38;5;74m",
    "info": "\033[38;5;179m",
    "muted": "\033[38;5;245m",
    "panel": "\033[48;5;236m",
    "panel_alt": "\033[48;5;238m",
    "error": "\033[38;5;196m",
    "yellow": "\033[38;5;222m",
    "light_yellow": "\033[38;5;230m",
    "green": "\033[38;5;108m",
    "pink": "\033[38;5;218m",
    "purple": "\033[38;5;183m",
    "orange": "\033[38;5;208m",
    "blue": "\033[38;5;111m",
    "cyan": "\033[38;5;109m",
}
