import os
import platform
import shutil
import subprocess
import sys


MODEL = os.getenv("FERRET_MODEL", "llama3.2")

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def clear_terminal_full():
    if os.name == "nt":
        os.system("cls")
        sys.stdout.write("\033[3J")
        sys.stdout.flush()
    else:
        sys.stdout.write("\033[3J\033[H\033[2J")
        sys.stdout.flush()


def run_cmd(cmd, check=False, **kwargs):
    try:
        return subprocess.run(cmd, check=check, **kwargs)
    except FileNotFoundError:
        return None


def check_python(min_version=(3, 10)):
    current = sys.version_info
    print(f"{CYAN}Python version: {current.major}.{current.minor}.{current.micro}{RESET}")
    if current < min_version:
        print(f"{RED}Python {min_version[0]}.{min_version[1]}+ is required. Exiting.{RESET}")
        sys.exit(1)


def ensure_package(pkg_name):
    try:
        __import__(pkg_name)
        print(f"{GREEN}{pkg_name} is already installed{RESET}")
    except ImportError:
        print(f"{YELLOW}{pkg_name} not found - installing...{RESET}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
        print(f"{GREEN}Installed {pkg_name}{RESET}")


def check_ollama_cli():
    if shutil.which("ollama"):
        print(f"{GREEN}Ollama CLI is installed{RESET}")
        return True

    print(f"{YELLOW}Ollama CLI not found.{RESET}")
    return False


def install_ollama_linux():
    print(f"{YELLOW}Installing Ollama on Linux...{RESET}")
    subprocess.run(["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], check=True)
    print(f"{GREEN}Installed Ollama{RESET}")


def prompt_install_ollama_windows():
    print(f"{YELLOW}Please install Ollama manually on Windows:{RESET}")
    print("Download from https://ollama.com/download (Windows installer)")
    print("Then re-run this installer once Ollama is installed.")


def ensure_ollama_installed():
    if check_ollama_cli():
        return

    system = platform.system()
    if system == "Linux":
        install_ollama_linux()
    elif system == "Windows":
        prompt_install_ollama_windows()
        sys.exit(1)
    else:
        print(f"{RED}Unsupported OS for automatic install: {system}{RESET}")
        sys.exit(1)


def ensure_model_downloaded(model):
    print(f"{YELLOW}Checking for model '{model}'...{RESET}")
    result = run_cmd(["ollama", "list"], capture_output=True, text=True)
    normalized_model = model.lower().strip()
    installed = result.stdout.lower() if result else ""
    if (
        result
        and (
            normalized_model in installed
            or f"{normalized_model}:latest" in installed
        )
    ):
        print(f"{GREEN}Model '{model}' already downloaded{RESET}")
        return

    print(f"{YELLOW}Model not detected - downloading...{RESET}")
    run_cmd(["ollama", "pull", model], check=True)
    print(f"{GREEN}Model '{model}' downloaded{RESET}")


if __name__ == "__main__":
    clear_terminal_full()
    print(f"{CYAN}--- Ferret AI Environment Setup ---{RESET}")
    print(f"{CYAN}Default local model: {MODEL}{RESET}\n")

    check_python(min_version=(3, 10))

    ensure_package("requests")
    ensure_package("flask")
    ensure_package("pyperclip")

    ensure_ollama_installed()
    ensure_model_downloaded(MODEL)

    print(f"\n{GREEN}Setup completed successfully!{RESET}")
    print(f"{CYAN}Ferret is ready as a local everyday assistant.{RESET}")
    print(f"{CYAN}Run the web app with: python app.py{RESET}")
    print(f"{CYAN}Run terminal mode with: python terminalAI/main.py{RESET}")
