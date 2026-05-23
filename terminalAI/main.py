# ur own AI, made by Mathus Souza, GitHub: https://github.com/loavy
from ai_core.engine import FerretAI

def main():
    try:
        app = FerretAI()
        app.chat()
    except KeyboardInterrupt:
        print("\nExiting safely...")
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
# ur own AI, made by Mathus Souza, GitHub: https://github.com/loavy
