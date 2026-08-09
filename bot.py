import os
import time
import random
from instagrapi import Client

HEART_EMOJIS = ["💚", "💙", "❤️", "🖤", "🤎", "💛", "💜", "🧡", "🤍", "🩶", "🩷"]

def generate_formatted_block(base_text: str, selected_heart: str, line_count: int = 40) -> str:
    lines = [f"{base_text} <{selected_heart}>" for _ in range(line_count)]
    return "\n\n".join(lines)

def main():
    print("[+] Initializing lightweight Instagram client...")
    cl = Client()
    session_file = "session.json"

    if os.path.exists(session_file):
        print("[+] Loading saved session tokens...")
        cl.load_settings(session_file)
    else:
        print("[!] Error: session.json not found!")
        return

    threads = cl.direct_threads(amount=1)
    if threads:
        thread = threads[0]
        print(f"[+] Connected successfully! Active thread ID: {thread.id}")
    else:
        print("[!] No direct threads found.")

if __name__ == "__main__":
    main()
