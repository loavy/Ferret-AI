import os
import sys
import json
import time
import random
import requests
import threading
import textwrap
from datetime import datetime
from pathlib import Path

# Internal imports from our package
from .config import BASE_COMPANION_PROMPT, CONFIG, PERSONAS, C
from .utils import _print_banner, _typing_indicator, _get_terminal_width
from . import FerretAIInit

# Clipboard support
try:
    import pyperclip
    CLIPBOARD_ENABLED = True
except ImportError:
    CLIPBOARD_ENABLED = False

# --- FERRET AI CLASS ---
class FerretAI(FerretAIInit):
    # --- TEXT CHUNKING ---
    def _chunk_text(self, text, size=1200, overlap=200):
        chunks, start = [], 0
        while start < len(text):
            end = start + size
            chunks.append(text[start:end])
            start += size - overlap
        return chunks

    # --- PERSONA SELECTION ---
    def _select_persona(self):
        print(f"\n{C['brand']}{C['bold']}Choose a conversation style{C['reset']}")
        for i, (key, desc) in enumerate(PERSONAS.items(), start=1):
            short_desc = desc.replace(BASE_COMPANION_PROMPT, "").strip()
            print(f"  {C['cyan']}{i}{C['reset']} {C['orange']}{key.ljust(9)}{C['reset']} {C['muted']}{short_desc[:92]}{C['reset']}")
        
        choice = input("Persona/Number: ").strip().lower()

        # Map numbers to persona keys
        persona_keys = list(PERSONAS.keys())
        if choice in PERSONAS:
            selected_persona = choice
        elif choice.isdigit() and 1 <= int(choice) <= len(persona_keys):
            selected_persona = persona_keys[int(choice)-1]
        else:
            print("Invalid input, defaulting to friend")
            selected_persona = persona_keys[0]

        # Save the description in CONFIG, but return the name
        CONFIG["persona"] = PERSONAS[selected_persona]
        self.messages.append({"role": "system", "content": CONFIG["persona"]})

        print(f"{C['green']}Style set:{C['reset']} {C['ai']}{selected_persona}{C['reset']}\n")

    # --- HELP MENU ---
    def _show_help(self):
        print(f"""
{C['brand']}{C['bold']}Ferret AI Help Menu{C['reset']}

{C['info']}Core Commands:{C['reset']}
  /help                     Show this menu
  /clear                    Reset conversation context
  /exit                     Quit application
  /code <lang>              Enter multi-line code mode
  /copy                     Copy latest code block
  /copy <num>               Copy code block from latest AI response
  /copy list                Show latest response code blocks
  /style                    Change conversation style

{C['info']}File Commands:{C['reset']}
  /f | /file <path>              Send file to AI
  /f | /file --summary <path>    Get concise summary
  /f | /file --explain <path>    Detailed explanation
  /f | /file --refactor <path>   Improve and return full code

{C['info']}Project Commands:{C['reset']}
  /p | /project add <folder>     Index project directory
  /p | /project list             Show indexed files
  /p | /project remove           Unload project
  /p | /project ask <question>   Ask question about project

{C['yellow']}Examples:{C['reset']}
  /file main.py | /f main.py
  /file --refactor app.js | /f --refactor app.js
  /project add ./my_app | /p add ./my_app
  /project ask how login works? | /p ask how login works?
""")

    
    # Clean tertminal
    def clear_terminal_full(self):
        if os.name == 'nt':
            os.system('cls')
            # ANSI escape for scrollback buffer clear (Windows Terminal supports this)
            sys.stdout.write("\033[3J")
            sys.stdout.flush()
        else:
            # Clear scrollback, move cursor home, clear screen
            sys.stdout.write("\033[3J\033[H\033[2J")
            sys.stdout.flush()

    # --- ENVIRONMENT SETUP ---
    def _setup_env(self):
        # Ensure log directory exists
        if not os.path.exists(CONFIG["log_dir"]):
            os.makedirs(CONFIG["log_dir"])

        # Clear the terminal and show banner
        self.clear_terminal_full()
        _print_banner()

        # Environment info
        print(f"{C['code_border']}+----------------------------- Session ------------------------------+{C['reset']}")
        print(f"{C['code_border']}|{C['reset']} {C['pink']}Model{C['reset']}    {C['muted']}->{C['reset']} {C['ai_alt']}{CONFIG['model']}{C['reset']}")
        print(f"{C['code_border']}|{C['reset']} {C['orange']}Ask{C['reset']}      {C['muted']}->{C['reset']} everyday questions, writing, planning, studying, code")
        print(f"{C['code_border']}|{C['reset']} {C['green']}Commands{C['reset']} {C['muted']}->{C['reset']} {C['cyan']}/clear{C['reset']} {C['muted']}|{C['reset']} {C['cyan']}/exit{C['reset']} {C['muted']}|{C['reset']} {C['cyan']}/style{C['reset']} {C['muted']}|{C['reset']} {C['cyan']}/copy{C['reset']} {C['muted']}|{C['reset']} {C['cyan']}/help{C['reset']}")
        print(f"{C['code_border']}|{C['reset']} {C['yellow']}File{C['reset']}     {C['muted']}->{C['reset']} {C['cyan']}/file <path>{C['reset']} {C['muted']}|{C['reset']} --summary {C['muted']}|{C['reset']} --explain {C['muted']}|{C['reset']} --refactor")
        print(f"{C['code_border']}|{C['reset']} {C['purple']}Project{C['reset']}  {C['muted']}->{C['reset']} {C['cyan']}/project add <dir>{C['reset']} {C['muted']}|{C['reset']} list {C['muted']}|{C['reset']} ask <question>")
        print(f"{C['code_border']}|{C['reset']} {C['blue']}Logs{C['reset']}     {C['muted']}->{C['reset']} {CONFIG['log_dir']}")
        print(f"{C['code_border']}+--------------------------------------------------------------------+{C['reset']}")
        print(f"{C['yellow']}Tip:{C['reset']} Use {C['cyan']}/style{C['reset']} for tone, {C['cyan']}/copy{C['reset']} for the latest code block.\n")

        # Friendly greeting
        greetings = [
            "Hey, I'm here. What are we thinking through today?",
            "Ready when you are. Bring me the question, the bug, or the messy thought.",
            "Fresh session. We can keep it simple and useful.",
            "Good to see you. What needs figuring out?",
            "Let's take it one clear step at a time."
        ]
        print(f"{C['ai']}Ferret:{C['reset']} {C['ai_alt']}{random.choice(greetings)}{C['reset']}\n")

    # --- LOGGING ---
    def log_interaction(self, user_text, ai_text):
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] USER: {user_text}\n[{timestamp}] AI: {ai_text}\n{'-'*30}\n")

    # --- CONTEXT BAR ---
    def _context_bar(self, ctx_size):
        ratio = min(ctx_size / CONFIG["max_context_messages"], 1.0)
        bar_length = 12
        filled = int(bar_length * ratio)
        empty = bar_length - filled
        bar = "#" * filled + "-" * empty
        color = C['context'] if ratio <= 0.4 else C['info'] if ratio <= 0.75 else C['error']
        return f"{C['muted']}context {color}[{bar}] {int(ratio*100)}%{C['reset']}"

    # --- CODE BLOCK RENDERING ---
    def _normalize_code_block(self, code_text):
        lines = code_text.strip().split("\n")
        if lines and lines[0].startswith("```"):
            first = lines[0].strip().strip("`").strip()
            language = first or ""
            lines = lines[1:]
        else:
            language = ""
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        if not language and len(lines) > 1:
            possible_language = lines[0].strip()
            if (
                possible_language
                and len(possible_language) <= 24
                and " " not in possible_language
                and all(char.isalnum() or char in "_+-#." for char in possible_language)
            ):
                language = possible_language
                lines = lines[1:]

        return language, "\n".join(lines).strip("\n")

    def _render_code_block(self, code_text, show_gutter=True, block_number=None):
        language, clean_code = self._normalize_code_block(code_text)
        lines = clean_code.split("\n") if clean_code else [""]

        term_width = _get_terminal_width()
        gutter = f"{C['code_border']}|{C['reset']}"
        max_line_width = term_width - len(gutter) - 5
        wrapped_lines = []

        for line in lines:
            wrapped_lines.extend(textwrap.wrap(line, width=max_line_width) or [""])

        if show_gutter:
            label = f"code block {block_number}" if block_number is not None else "code block"
            if language:
                label += f" ({language})"
            print(f"\n{C['panel']}{C['ai_alt']} {label} {C['reset']} {C['muted']}use{C['reset']} {C['cyan']}/copy {block_number or 1}{C['reset']}")
            for idx, line in enumerate(wrapped_lines, start=1):
                number_str = str(idx).rjust(3)
                line_color = C['light_yellow'] if idx % 2 else C['ai_alt']
                print(f"{gutter} {C['muted']}{number_str}{C['reset']} {line_color}{line.ljust(max_line_width)}{C['reset']}")
        return clean_code

    # --- PYTHON SYMBOL EXTRACTION ---
    def _extract_python_blocks(self, content):
        blocks = []
        lines = content.splitlines()
        current_block, current_name = [], None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("def ") or stripped.startswith("class "):
                if current_block:
                    blocks.append((current_name, "\n".join(current_block)))
                    current_block = []
                current_name = stripped.split("(")[0].replace("def ", "").replace("class ", "").strip()
                current_block.append(line)
            elif current_block:
                current_block.append(line)
        if current_block:
            blocks.append((current_name, "\n".join(current_block)))
        return blocks

    def _extract_imports(self, content):
        imports = []
        for line in content.splitlines():
            if line.strip().startswith(("import ", "from ")):
                imports.append(line.strip())
        return imports

    def _score_block(self, question, block_text, block_name=None):
        score = 0
        q_words = question.lower().split()
        text = block_text.lower()
        for word in q_words:
            score += text.count(word) * 2
            if block_name and word in block_name.lower():
                score += 5
        if "traceback" in question.lower():
            score += text.count("raise") * 3
        return score

    def _detect_traceback_target(self, question):
        if "Traceback" not in question:
            return None
        lines = question.splitlines()
        for line in lines:
            if ".py" in line and "File" in line:
                try:
                    file_part = line.split('"')[1]
                    return os.path.basename(file_part)
                except:
                    pass
        return None

    # --- MAIN CHAT LOOP ---
    def chat(self):
        short_commands = {
            "/p": "/project",
            "/f": "/file",
            "/h": "/help",
            "/rl": "/resetlog"
        }
        while True:
            try:
                ctx_size = len(self.messages) - 1
                prompt = f"{self._context_bar(ctx_size)}\n{C['prompt']}{C['bold']}you{C['reset']} {C['muted']}>{C['reset']} "
                first_line = input(prompt).strip()
                if not first_line:
                    continue

                # Replace short commands with full commands without mangling /project or /file.
                for short, full in short_commands.items():
                    if first_line == short or first_line.startswith(short + " "):
                        first_line = first_line.replace(short, full, 1)
                        break

                cmd = first_line.lower()

                # --- EXIT ---
                if cmd == '/exit':
                    print(f"{C['yellow']}Signing off.{C['reset']}")
                    break

                # --- HELP ---
                if cmd == '/help':
                    self._show_help()
                    continue

                # --- STYLE ---
                if cmd == '/style':
                    self._select_persona()
                    self.messages = [{"role": "system", "content": CONFIG["persona"]}]
                    print(f"{C['brand']}Started a fresh chat with the new style.{C['reset']}\n")
                    continue

                # --- REBUILD THE LOG ---
                if cmd == '/resetlog':
                    os.makedirs(CONFIG["log_dir"], exist_ok=True)
                    with open(self.log_file, "w", encoding="utf-8") as f:
                        f.write(f"Ferret AI terminal log reset at {datetime.now():%Y-%m-%d %H:%M:%S}\n")
                    print(f"\n{C['brand']}Log reset:{C['reset']} {self.log_file}\n")
                    continue

                # --- CLEAR CONTEXT ---
                if cmd == '/clear':
                    self.messages = [{"role": "system", "content": CONFIG["persona"]}]
                    self.code_blocks = []
                    self.last_code_blocks = []
                    self._setup_env()
                    print(f"{C['brand']}Context cleared. Fresh chat ready.{C['reset']}\n")
                    continue

                # --- CODE MODE ---
                if cmd.startswith('/code'):
                    parts = first_line.split()
                    lang = parts[1] if len(parts) > 1 else ""

                    question = input(f"\n{C['yellow']}<Question> {C['reset']}")

                    print(f"\n{C['brand']}Entering code mode. Type '/end' to send.{C['reset']}\n")
                    lines = []
                    while True:
                        line = input(f"{C['code']}... {C['reset']}")
                        if line.strip().lower() == "/end":
                            break
                        lines.append(line)

                    if not lines:
                        print(f"{C['yellow']}No code entered.{C['reset']}")
                        continue

                    user_input = f"Question: {question}\nCode ({lang}):\n" + "\n".join(lines) + "\n"

                # --- COPY CODE BLOCK ---
                elif cmd.startswith('/copy'):
                    parts = cmd.split()
                    if not self.last_code_blocks and not self.code_blocks:
                        print(f"{C['yellow']}No code blocks to copy yet.{C['reset']}")
                        continue

                    if len(parts) == 1:
                        selected = self.last_code_blocks[-1] if self.last_code_blocks else self.code_blocks[-1]
                        label = "latest code block"
                    elif len(parts) == 2 and parts[1] == "list":
                        if not self.last_code_blocks:
                            print(f"{C['yellow']}No code blocks in the latest response. Use /copy for the newest saved block.{C['reset']}")
                        else:
                            print(f"{C['info']}Latest response code blocks:{C['reset']}")
                            for idx, block in enumerate(self.last_code_blocks, start=1):
                                first_line = block.strip().splitlines()[0] if block.strip() else "(empty)"
                                preview = first_line[:60]
                                print(f"  {idx}. {preview}")
                        continue
                    elif len(parts) == 2 and parts[1].isdigit():
                        idx = int(parts[1]) - 1
                        if not 0 <= idx < len(self.last_code_blocks):
                            print(f"{C['yellow']}That number is not in the latest response. Use /copy list to see available blocks.{C['reset']}")
                            continue
                        selected = self.last_code_blocks[idx]
                        label = f"latest response code block {idx+1}"
                    else:
                        print(f"{C['yellow']}Usage: /copy | /copy <number> | /copy list{C['reset']}")
                        continue

                    if CLIPBOARD_ENABLED:
                        pyperclip.copy(selected)
                        print(f"{C['green']}Copied {label}.{C['reset']}")
                    else:
                        print(f"{C['yellow']}pyperclip not installed.{C['reset']}")
                    continue

                # --- PROJECT COMMANDS ---
                elif cmd.startswith('/project'):
                    parts = first_line.split(maxsplit=2)
                    if len(parts) == 1:
                        print(f"{C['yellow']}Usage: /project add|remove|list|ask{C['reset']}")
                        continue
                    sub = parts[1]

                    # --- ADD PROJECT ---
                    if sub == "add":
                        if len(parts) < 3:
                            print(f"{C['yellow']}Usage: /project add <folder>{C['reset']}")
                            continue
                        folder = parts[2].strip('"')
                        if not os.path.isdir(folder):
                            print(f"{C['error']}Directory not found.{C['reset']}")
                            continue
                        self.project_root = folder
                        self.project_index = {}
                        self.project_chunks = []
                        self.project_blocks = []
                        self.symbol_index = {}
                        print(f"{C['info']}Indexing project with symbol extraction...{C['reset']}")
                        allowed_ext = (".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".lua", ".c", ".cpp", ".md", ".toml", ".yaml", ".yml")
                        ignored_dirs = {".git", ".venv", "venv", "env", "__pycache__", "node_modules", "dist", "build", ".next", ".pytest_cache"}
                        for root, dirs, files in os.walk(folder):
                            dirs[:] = [d for d in dirs if d not in ignored_dirs]
                            for file in files:
                                if not file.endswith(allowed_ext):
                                    continue
                                path = os.path.join(root, file)
                                rel = os.path.relpath(path, folder)
                                try:
                                    with open(path, "r", encoding="utf-8") as f:
                                        content = f.read()
                                except:
                                    continue

                                imports = self._extract_imports(content)
                                blocks = self._extract_python_blocks(content) if file.endswith(".py") else [("file_scope", content[:8000])]
                                self.project_index[rel] = {"chunks": self._chunk_text(content), "size": len(content), "blocks": blocks, "imports": imports}

                                for name, block in blocks:
                                    self.project_blocks.append((rel, block, name))
                                    if name:
                                        self.symbol_index.setdefault(name, []).append((rel, block))
                                for chunk in self.project_index[rel]["chunks"]:
                                    self.project_chunks.append((rel, chunk))

                        print(f"{C['green']}Indexed {len(self.project_index)} files, {len(self.project_blocks)} code blocks.{C['reset']}")
                        continue

                    # --- REMOVE PROJECT ---
                    elif sub == "remove":
                        self.project_root = None
                        self.project_index = {}
                        self.project_chunks = []
                        self.project_blocks = []
                        self.symbol_index = {}
                        print(f"{C['brand']}Project removed.{C['reset']}")
                        continue

                    # --- LIST PROJECT FILES ---
                    elif sub == "list":
                        if not self.project_index:
                            print(f"{C['yellow']}No project loaded.{C['reset']}")
                        else:
                            print(f"{C['info']}Project files:{C['reset']}")
                            for file in self.project_index.keys():
                                print(f" - {file}")
                        continue

                    # --- ASK PROJECT ---
                    elif sub == "ask":
                        if not self.project_blocks:
                            print(f"{C['yellow']}No project loaded.{C['reset']}")
                            continue
                        if len(parts) < 3:
                            print(f"{C['yellow']}Usage: /project ask <question>{C['reset']}")
                            continue
                        question = parts[2]
                        traceback_file = self._detect_traceback_target(question)
                        scored = []

                        for path, block, name in self.project_blocks:
                            score = self._score_block(question, block, name)
                            if traceback_file and traceback_file in path:
                                score += 20
                            if score > 0:
                                scored.append((score, path, block, name))

                        if not scored:
                            print(f"{C['yellow']}No strong matches found. Using top blocks.{C['reset']}")
                            scored = [(1, p, b, n) for p, b, n in self.project_blocks[:5]]

                        scored.sort(reverse=True, key=lambda x: x[0])
                        MAX_CONTEXT = 12000
                        used = 0
                        injection = ""
                        used_files = set()
                        for score, path, block, name in scored:
                            if used + len(block) > MAX_CONTEXT:
                                break
                            injection += f"\n[File: {path} | Symbol: {name} | Score: {score}]\n```\n{block}\n```\n"
                            used += len(block)
                            used_files.add(path)

                        print(f"{C['info']}Using {len(used_files)} files ({used} chars).{C['reset']}")
                        user_input = f"Answer using the relevant project code below. Cite file names when useful.\n{injection}\nQuestion: {question}\n"

                # --- FILE COMMANDS ---
                elif cmd.startswith('/file'):
                    parts = first_line.split()
                    if len(parts) < 2:
                        print(f"{C['yellow']}Usage: /file <path>{C['reset']}")
                        continue
                    mode, file_path = ("normal", "")
                    if parts[1].startswith("--"):
                        mode = parts[1][2:]
                        if len(parts) < 3:
                            print(f"{C['yellow']}Missing file path.{C['reset']}")
                            continue
                        file_path = parts[2]
                    else:
                        file_path = parts[1]
                    file_path = file_path.strip('"')
                    if not os.path.exists(file_path):
                        print(f"{C['error']}File not found: {file_path}{C['reset']}")
                        continue
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except Exception as e:
                        print(f"{C['error']}Could not read file: {e}{C['reset']}")
                        continue
                    max_chars = CONFIG["max_file_chars"]
                    if len(content) > max_chars:
                        print(f"{C['yellow']}File too large. Truncating to {max_chars} characters.{C['reset']}")
                        content = content[:max_chars]
                    filename = os.path.basename(file_path)
                    if mode == "summary":
                        prompt_prefix = "Provide a concise summary of this file."
                    elif mode == "explain":
                        prompt_prefix = "Explain in detail what this file does, including architecture and logic."
                    elif mode == "refactor":
                        prompt_prefix = (
                            "Refactor and improve this file. "
                            "Improve readability, structure, and performance. "
                            "Return the improved full code."
                        )
                    else:
                        prompt_prefix = f"Here is the content of file `{filename}`:"
                    user_input = f"{prompt_prefix}\n\nFile name: `{filename}`\n\n```\n{content}\n```"
                    print(f"{C['green']}Loaded file: {filename} ({len(content)} chars) | Mode: {mode}{C['reset']}")

                else:
                    user_input = first_line

                # --- SEND TO AI ---
                self.messages.append({"role": "user", "content": user_input})
                stop_event = threading.Event()
                spinner_thread = threading.Thread(target=_typing_indicator, args=(stop_event,))
                spinner_thread.start()

                try:
                    response = requests.post(
                        CONFIG["url"],
                        json={"model": CONFIG["model"], "messages": self.messages, "stream": True},
                        stream=True,
                        timeout=20
                    )
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    stop_event.set()
                    spinner_thread.join()
                    print(f"\n{C['error']}Network error: {e}{C['reset']}")
                    continue

                stop_event.set()
                spinner_thread.join()
                print(f"\n{C['brand']}{C['bold']}Ferret{C['reset']} {C['muted']}>{C['reset']} ", end="")

                full_response = ""
                in_code_block = False
                code_buffer = ""
                response_code_blocks = []
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line.decode("utf-8"))
                    content = chunk.get("message", {}).get("content", "")
                    full_response += content
                    while content:
                        if content.startswith("```"):
                            in_code_block = not in_code_block
                            content = content[3:]
                            if not in_code_block and code_buffer:
                                code_text = "```\n" + code_buffer + "\n```"
                                clean_code = self._render_code_block(
                                    code_text,
                                    block_number=len(response_code_blocks) + 1,
                                )
                                self.code_blocks.append(clean_code)
                                response_code_blocks.append(clean_code)
                                code_buffer = ""
                            continue
                        if in_code_block:
                            newline_pos = content.find("\n")
                            if newline_pos != -1:
                                code_buffer += content[:newline_pos] + "\n"
                                content = content[newline_pos+1:]
                            else:
                                code_buffer += content
                                content = ""
                        else:
                            for char in content:
                                sys.stdout.write(char)
                                sys.stdout.flush()
                                time.sleep(CONFIG["typing_speed"])
                            content = ""

                if code_buffer.strip():
                    code_text = "```\n" + code_buffer.strip() + "\n```"
                    clean_code = self._render_code_block(
                        code_text,
                        block_number=len(response_code_blocks) + 1,
                    )
                    self.code_blocks.append(clean_code)
                    response_code_blocks.append(clean_code)

                print("\n")
                self.last_code_blocks = response_code_blocks
                self.log_interaction(user_input, full_response)
                self.messages.append({"role": "assistant", "content": full_response})

            except KeyboardInterrupt:
                print(f"\n{C['yellow']}Interrupted.{C['reset']}")
                break
            except Exception as e:
                print(f"\n{C['error']}Fault: {e}{C['reset']}\n")
# ur own AI, made by Mathus Souza, GitHub: https://github.com/loavy
