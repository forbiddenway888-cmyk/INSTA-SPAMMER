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

    target_thread_id = "340282366841710301281155341573245163458"
    print(f"[+] Starting command listener loop for thread: {target_thread_id}")

    processed_message_ids = set()

    # Seed initial messages so it ignores historical chat logs on boot
    try:
        initial_thread = cl.direct_thread(target_thread_id)
        for m in initial_thread.messages[:5]:
            processed_message_ids.add(m.id)
        print("[+] Synced chat history. Listening for new commands...")
    except Exception as e:
        print(f"[!] Warning during initial sync: {e}")

    while True:
        try:
            thread = cl.direct_thread(target_thread_id)
            messages = thread.messages
            
            if messages:
                latest = messages[0]
                msg_id = latest.id
                msg_text = latest.text if latest.text else ""
                
                if msg_id not in processed_message_ids:
                    processed_message_ids.add(msg_id)
                    
                    if msg_text.startswith("^"):
                        print(f"[+] Command received: {msg_text}")
                        
                        if msg_text == "^ping":
    start_t = time.time()
    cl.account_info()  # Lightweight API network ping
    end_t = time.time()
    
    latency_ms = round((end_t - start_t) * 1000, 2)
    cl.direct_send(f"Pong! 🏓 Live API Latency: {latency_ms}ms | Blazing fast ⚡", thread_ids=[target_thread_id])
    print(f"[+] Responded to ^ping in {latency_ms}ms!")
            
            time.sleep(3) # Safe polling interval to avoid rate limits
            
        except Exception as e:
            print(f"[!] Error in listener loop: {e}")
            time.sleep(0.1)

if __name__ == "__main__":
    main()
