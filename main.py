import os
from instagrapi import Client

def main():
    print("[+] Initializing light API client...")
    cl = Client()

    username = os.getenv("INSTA_USERNAME")
    password = os.getenv("INSTA_PASSWORD")
    session_file = "session.json"

    # Load previously saved session if it exists to avoid repeated logins
    if os.path.exists(session_file):
        print("[+] Loading saved session...")
        cl.load_settings(session_file)

    try:
        print("[+] Logging into Instagram via API...")
        cl.login(username, password)
        # Save refreshed session settings
        cl.dump_settings(session_file)
        print("[+] Login successful!")
    except Exception as e:
        print(f"[!] Login failed: {e}")
        return

    # Target chat thread or user ID
    # For instagrapi, you can fetch direct threads or send messages directly to user IDs / thread IDs
    print("[+] Fetching direct threads...")
    threads = cl.direct_threads(amount=5)
    
    if threads:
        thread = threads[0]
        print(f"[+] Found thread ID: {thread.id}")
        
        # Send a test message
        test_msg = "🤖 Light API Bot online and connected successfully!"
        cl.direct_send(test_msg, thread_ids=[thread.id])
        print(f"[+] Test message sent to thread: {thread.id}")
    else:
        print("[!] No active direct threads found.")

if __name__ == "__main__":
    main()
