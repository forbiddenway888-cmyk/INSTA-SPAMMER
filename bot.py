import os
import time
import random
import asyncio
import requests
from instagrapi import Client

HEART_EMOJIS = ["💚", "💙", "❤️", "🖤", "🤎", "💛", "💜", "🧡", "🤍", "🩶", "🩷"]

def generate_formatted_block(base_text: str, selected_heart: str, line_count: int = 40) -> str:
    lines = [f"{base_text} <{selected_heart}>" for _ in range(line_count)]
    return "\n\n".join(lines)

def get_free_proxy():
    while True:
        try:
            print("[+] Scraping fresh public proxies...", flush=True)
            url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=yes"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                proxies = [line.strip() for line in response.text.splitlines() if line.strip()]
                random.shuffle(proxies)
                
                print(f"[+] Testing batch of {min(len(proxies), 30)} proxies...", flush=True)
                for p in proxies[:30]:
                    test_proxy = {"http": f"http://{p}", "https": f"http://{p}"}
                    try:
                        # Test if the proxy can successfully reach Instagram
                        r = requests.get("https://www.instagram.com", proxies=test_proxy, timeout=3)
                        if r.status_code == 200:
                            print(f"[+] Verified working proxy locked: {p}", flush=True)
                            return f"http://{p}"
                    except:
                        continue
                        
            print("[!] No working proxies in this batch. Retrying scraper in 3 seconds...", flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"[!] Proxy scraper error: {e}. Retrying...", flush=True)
            time.sleep(3)

class AsyncInstagramCommandBot:
    def __init__(self, client: Client, target_thread_id: str, prefix: str = "^"):
        self.cl = client
        self.target_thread_id = target_thread_id
        self.prefix = prefix
        self.is_running = True
        self.processed_message_ids = set()
        self.active_spam_task = None
        self.stop_flag = asyncio.Event()

    async def start_listener(self):
        print("[+] Initializing Hyper-Speed Async API Listener...", flush=True)

        try:
            # Wrap network calls with a 6s timeout so hanging proxies never freeze the bot
            initial_thread = await asyncio.wait_for(
                asyncio.to_thread(self.cl.direct_thread, self.target_thread_id),
                timeout=6.0
            )
            for m in initial_thread.messages[:5]:
                self.processed_message_ids.add(m.id)
            print("[+] Synced chat history. Hyper-speed polling active! ⚡", flush=True)
        except asyncio.TimeoutError:
            print("[!] Proxy hanging! Dropping dead proxy and switching to direct connection...", flush=True)
            self.cl.set_proxy(None)  # Remove dead proxy
            try:
                initial_thread = await asyncio.to_thread(self.cl.direct_thread, self.target_thread_id)
                for m in initial_thread.messages[:5]:
                    self.processed_message_ids.add(m.id)
                print("[+] Synced chat history via direct connection!", flush=True)
            except Exception as e:
                print(f"[!] Direct sync error: {e}", flush=True)
        except Exception as e:
            print(f"[!] Warning during initial sync: {e}", flush=True)

        while self.is_running:
            try:
                thread = await asyncio.wait_for(
                    asyncio.to_thread(self.cl.direct_thread, self.target_thread_id),
                    timeout=5.0
                )
                messages = thread.messages
                
                if messages:
                    latest = messages[0]
                    msg_id = latest.id
                    msg_text = latest.text if latest.text else ""
                    
                    if msg_id not in self.processed_message_ids:
                        self.processed_message_ids.add(msg_id)
                        
                        if msg_text.startswith(self.prefix):
                            print(f"[+] Instant Command Caught: {msg_text}", flush=True)
                            asyncio.create_task(self.process_command(msg_text))
                
                await asyncio.sleep(0.25)
                
            except asyncio.TimeoutError:
                # Skip silently if a poll cycle times out, preventing freezes
                await asyncio.sleep(1)
            except Exception as e:
                print(f"[!] Error in hyper-speed loop: {e}", flush=True)
                await asyncio.sleep(1)
                
    async def process_command(self, full_text: str):
        parts = full_text.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == f"{self.prefix}ping":
            start_t = time.time()
            try:
                await asyncio.to_thread(self.cl.account_info)
                end_t = time.time()
                latency_ms = round((end_t - start_t) * 1000, 2)
                await asyncio.to_thread(
                    self.cl.direct_answer,
                    self.target_thread_id,
                    f"Pong! 🏓 Latency: {latency_ms}ms | Bot active!"
                )
            except Exception as e:
                print(f"[!] Ping command error: {e}", flush=True)

        elif cmd == f"{self.prefix}spam":
            if not args:
                asyncio.create_task(asyncio.to_thread(self.cl.direct_answer, self.target_thread_id, "Usage: ^spam <text> [delay]"))
                return
            
            delay = 0.4
            spam_text = " ".join(args)
            
            if len(args) > 1:
                try:
                    possible_delay = float(args[-1])
                    delay = max(0.4, possible_delay)
                    spam_text = " ".join(args[:-1])
                except ValueError:
                    pass

            self.stop_flag.set()
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()

            self.stop_flag.clear()
            asyncio.create_task(asyncio.to_thread(self.cl.direct_answer, self.target_thread_id, f"⚡ Spam Active | Delay: {delay}s"))

            self.active_spam_task = asyncio.create_task(self.execute_spam_loop(spam_text, delay))

        elif cmd in [f"{self.prefix}unspam", f"{self.prefix}stop"]:
            self.stop_flag.set()
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
                self.active_spam_task = None
                asyncio.create_task(asyncio.to_thread(self.cl.direct_answer, self.target_thread_id, "🛑 Spam aborted successfully!"))
            else:
                asyncio.create_task(asyncio.to_thread(self.cl.direct_answer, self.target_thread_id, "⚠️ No active spam sequence running."))

    async def execute_spam_loop(self, base_text: str, delay: float):
        try:
            block_num = 1
            while not self.stop_flag.is_set():
                heart = random.choice(HEART_EMOJIS)
                payload = generate_formatted_block(base_text, heart, line_count=20)
                
                if self.stop_flag.is_set():
                    break

                try:
                    await asyncio.to_thread(
                        self.cl.direct_answer,
                        self.target_thread_id,
                        payload
                    )
                except Exception as e:
                    print(f"[!] Send error caught: {e}", flush=True)  # <-- This will print the exact reason
                    err_str = str(e)
                    if "403" in err_str or "1404006" in err_str:
                        await asyncio.sleep(2)
                    else:
                        await asyncio.sleep(1)
                    continue

                block_num += 1
                safe_delay = max(0.4, delay)
                if not self.stop_flag.is_set():
                    await asyncio.sleep(safe_delay)
                    
        except asyncio.CancelledError:
            print("[!] Spam loop cancelled.", flush=True)

async def main():
    print("[+] Starting main initialization...", flush=True)
    cl = Client()
    
    proxy = get_free_proxy()
    if proxy:
        cl.set_proxy(proxy)
    else:
        print("[+] Running without proxy (direct connection)...", flush=True)
        
    cl.delay_range = [2, 4]
    
    session_file = "session.json"
    print(f"[+] Checking for {session_file}...", flush=True)
    
    if os.path.exists(session_file):
        print("[+] Loading saved session tokens...", flush=True)
        cl.load_settings(session_file)
        print("[+] Session loaded successfully!", flush=True)
    else:
        print("[!] Error: session.json not found!", flush=True)
        return

    target_thread_id = "340282366841710301281155341573245163458"
    print("[+] Starting bot listener...", flush=True)
    
    bot = AsyncInstagramCommandBot(cl, target_thread_id, prefix="^")
    await bot.start_listener()

if __name__ == "__main__":
    asyncio.run(main())
