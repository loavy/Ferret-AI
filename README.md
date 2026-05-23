<div align="center">
  <img src="./static/img/icon.jpg" height="220" width="220" alt="Ferret AI icon">

  # Ferret AI
  ### A pretty local assistant for everyday thinking
</div>

Ferret AI is a local, privacy-first assistant powered by Ollama. It is meant to feel calm and friendly in the browser, colorful and pleasant in the terminal, and useful for more than code.

Use it for:

- everyday questions and second opinions
- writing, rewriting, and translation
- planning small projects or study sessions
- explaining concepts
- coding, debugging, reviewing, and refactoring
- summarizing files and old chat logs

## Default Model

Ferret now uses `llama3.2` by default.

That model is a good local daily-driver choice because it is small, general-purpose, multilingual, and lighter than bigger coding-focused models. It still handles code, but it is not limited to coding.

```bash
ollama pull llama3.2
```

You can override the model any time:

```powershell
$env:FERRET_MODEL = "deepseek-coder:6.7b"
python app.py
```

## Features

- Local Ollama chat with `llama3.2` by default
- Polished web interface with light/dark theme toggle
- Multiple web conversations without losing the current one
- Drag-and-drop log import so terminal logs can continue in the browser
- Terminal interface with colorful session UI
- Natural English and PT-BR behavior
- Streaming responses
- Code block copy in the web UI
- Better terminal `/copy` behavior:
  - `/copy` copies the newest code block
  - `/copy 1` copies block 1 from the latest response
  - `/copy list` shows latest response blocks
- `/style` command in terminal mode
- File summary, explanation, and refactor commands
- Project folder indexing for code questions
- Local daily logs in `logs_Ferret`

## Quick Start

```bash
git clone https://github.com/loavy/Ferret-AI.git
cd Ferret-AI
python installer.py
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Terminal mode:

```bash
python terminalAI/main.py
```

## Requirements

- Python 3.10+
- Ollama installed and running
- `llama3.2` pulled locally

Manual setup:

```bash
pip install -r requirements.txt
ollama pull llama3.2
python app.py
```

## Configuration

Ferret works without configuration, but these environment variables are supported:

```bash
FERRET_MODEL=llama3.2
FERRET_API_URL=http://localhost:11434/api/chat
FERRET_LOG_DIR=~/logs_Ferret
FERRET_MAX_HISTORY_MESSAGES=40
FERRET_MAX_FILE_CHARS=18000
```

PowerShell example:

```powershell
$env:FERRET_MODEL = "llama3.2"
python app.py
```

## Web Commands

```text
/clear              Start a fresh chat
/log                List saved chat logs
/log filename.txt   Summarize a saved log
```

## Web Conversations

The web UI keeps multiple conversations in the left panel. Click `New chat` to start another conversation without deleting the current one, then switch back any time from the list.

To continue an old session, drag a Ferret `.txt` log into the import box or click `Import log`. Ferret will reconstruct old `USER` and `AI` turns when the log uses the normal saved format, then the imported log becomes a normal conversation.

Use the conversation toggle in the top bar to hide or show the sidebar. Each conversation also has a delete button, and deleting the active chat automatically opens the next available one.

## Terminal Styles

Run:

```text
/style
```

Available styles:

- `friend` for everyday conversation
- `thinker` for careful explanations
- `writer` for wording, tone, translation, and structure
- `reviewer` for code review
- `debugger` for tracing bugs
- `concise` for shorter answers

## Terminal Commands

```text
/help                         Show commands
/style                        Change conversation style
/clear                        Reset conversation context
/exit                         Quit
/code <lang>                  Paste multi-line code, then send with /end
/copy                         Copy the newest code block
/copy <num>                   Copy a block from the latest AI response
/copy list                    List latest response code blocks
/file <path>                  Send a file to Ferret
/file --summary <path>        Summarize a file
/file --explain <path>        Explain a file
/file --refactor <path>       Ask for a refactor
/project add <folder>         Index a project folder
/project list                 Show indexed files
/project ask <question>       Ask about indexed code
/project remove               Unload the project
/resetlog                     Recreate today's terminal log
```

Shortcuts:

```text
/f   -> /file
/p   -> /project
/h   -> /help
/rl  -> /resetlog
```

## Troubleshooting

If the web UI says Ollama is offline:

```bash
ollama serve
```

If the model is missing:

```bash
ollama pull llama3.2
```

If dependencies are missing:

```bash
pip install -r requirements.txt
```

If the status says the model is missing but chat works, restart the Flask server so the latest status check code is running.

## Notes

Ferret is intentionally local-first. There are no cloud API keys, telemetry hooks, or remote model calls in the app code.
