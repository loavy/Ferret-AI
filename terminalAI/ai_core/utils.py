import shutil
import sys
import time

from .config import C


def _print_banner():
    banner = f"""
{C['brand']}{C['bold']}     ______                  _        ___    ___{C['reset']}
{C['orange']}{C['bold']}    |  ____|                | |      / _ \\  |_ _|{C['reset']}
{C['yellow']}{C['bold']}    | |__ ___ _ __ _ __ ___ | |_    / /_\\ \\  | |{C['reset']}
{C['green']}{C['bold']}    |  __/ _ \\ '__| '__/ _ \\| __|   |  _  |  | |{C['reset']}
{C['cyan']}{C['bold']}    | | |  __/ |  | | |  __/| |_    | | | | _| |_{C['reset']}
{C['purple']}{C['bold']}    |_|  \\___|_|  |_|  \\___| \\__|   \\_| |_/ \\___/{C['reset']}

{C['pink']}        local, thoughtful, lightweight{C['reset']}
{C['code_border']}  +----------------------------------------------------------+
  | {C['ai_alt']}Ask anything:{C['reset']}{C['code_border']} code, writing, planning, study, life.       |
  | {C['ai_alt']}Vibe:{C['reset']}{C['code_border']} calm answers, useful details, no cloud required. |
  +----------------------------------------------------------+{C['reset']}
"""
    print(banner)


def _typing_indicator(stop_event):
    spinner = ["|", "/", "-", "\\"]
    i = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r{C['ai']}{spinner[i % len(spinner)]}{C['reset']} thinking...")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 30 + "\r")


def _get_terminal_width(default=80):
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return default
