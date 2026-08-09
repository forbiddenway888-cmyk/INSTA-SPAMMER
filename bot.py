import os
import time
from instagrapi import Client

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

    # Verify connection by grabbing the latest thread
    threads = cl.direct_threads(amount=1)
    if threads:
        thread = threads[0]
        print(f"[+] Connected successfully! Active thread ID: {thread.id}")
    else:
        print("[!] No direct threads found.")

if __name__ == "__main__":
    main()
