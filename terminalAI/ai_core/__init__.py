import os
from datetime import datetime
from .config import CONFIG
from .utils import _print_banner

class FerretAIInit:
    def __init__(self):
        # Project / context
        self.project_index = {}
        self.project_chunks = []
        self.project_blocks = []
        self.symbol_index = {}
        self.project_root = None

        # Chat context
        self.messages = []
        self.code_blocks = []
        self.last_code_blocks = []

        self._select_persona()
        self.log_file = os.path.join(CONFIG["log_dir"], f"chat_TERM_{datetime.now().strftime('%Y%m%d')}.txt")
        self._setup_env()
# ur own AI, made by Mathus Souza, GitHub: https://github.com/loavy
