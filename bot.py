import os
import time
import random
import asyncio
from instagrapi import Client

HEART_EMOJIS = ["💚", "💙", "❤️", "🖤", "🤎", "💛", "💜", "🧡", "🤍", "🩶", "🩷"]

def generate_formatted_block(base_text: str, selected_heart: str, line_count: int = 40) -> str:
    lines = [f"{base_text} <{selected_heart}>" for _ in range(line_count)]
    return "\n\n".join(lines)

class AsyncInstagramCommandBot:
    def __init__(self, client: Client, target_thread_id: str, prefix: str = "^"):
        self.cl = client
        self.target_thread_id = target_thread_id
        self.prefix = prefix
        self.is_running = True
        self.processed_message_ids = set()
        self.active_spam_task = None
        self.stop_flag = asyncio.Event()  # Instant breaker flag

    async def start_listener(self):
        print(f"[+] Initializing Hyper-Speed Async API Listener...")

        try:
            initial_thread = await asyncio.to_thread(self.cl.direct_thread, self.target_thread_id)
            for m in initial_thread.messages[:5]:
                self.processed_message_ids.add(m.id)
            print("[+] Synced chat history. Hyper-speed polling active! ⚡")
        except Exception as e:
            print(f"[!] Warning during initial sync: {e}")

        while self.is_running:
            try:
                # Fetch latest messages with minimal overhead
                thread = await asyncio.to_thread(self.cl.direct_thread, self.target_thread_id)
                messages = thread.messages
                
                if messages:
                    latest = messages[0]
                    msg_id = latest.id
                    msg_text = latest.text if latest.text else ""
                    
                    if msg_id not in self.processed_message_ids:
                        self.processed_message_ids.add(msg_id)
                        
                        if msg_text.startswith(self.prefix):
                            print(f"[+] Instant Command Caught: {msg_text}")
                            asyncio.create_task(self.process_command(msg_text))
                
                # Pushed to 0.25s for maximum snap speed
                await asyncio.sleep(0.25)
                
            except Exception as e:
                print(f"[!] Error in hyper-speed loop: {e}")
                await asyncio.sleep(1)
                
    async def process_command(self, full_text: str):
        parts = full_text.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == f"{self.prefix}ping":
            start_t = time.time()
            await asyncio.to_thread(self.cl.account_info)
            end_t = time.time()
            
            latency_ms = round((end_t - start_t) * 1000, 2)
            await asyncio.to_thread(
                self.cl.direct_send,
                f"Pong! 🏓 Async API Latency: {latency_ms}ms | Blazing fast ⚡",
                thread_ids=[self.target_thread_id]
            )
            print(f"[+] Responded to ^ping in {latency_ms}ms!")

        elif cmd == f"{self.prefix}spam":
            if not args:
                asyncio.create_task(asyncio.to_thread(self.cl.direct_send, "Usage: ^spam <text> [delay]", thread_ids=[self.target_thread_id]))
                return
            
            delay = 0.05  # Ultra-fast flashing default speed
            spam_text = " ".join(args)
            
            if len(args) > 1:
                try:
                    possible_delay = float(args[-1])
                    delay = max(0.01, possible_delay)  # Allow blazing sub-second speeds
                    spam_text = " ".join(args[:-1])
                except ValueError:
                    pass

            # Instant kill switch for any existing spam
            self.stop_flag.set()
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()

            self.stop_flag.clear()
            asyncio.create_task(asyncio.to_thread(self.cl.direct_send, f"⚡ Hyper-Flash Spam Active | Delay: {delay}s", thread_ids=[self.target_thread_id]))

            self.active_spam_task = asyncio.create_task(self.execute_spam_loop(spam_text, delay))

        elif cmd in [f"{self.prefix}unspam", f"{self.prefix}stop"]:
            self.stop_flag.set()  # Triggers instant termination
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
                self.active_spam_task = None
                asyncio.create_task(asyncio.to_thread(self.cl.direct_send, "🛑 Spam aborted instantly!", thread_ids=[self.target_thread_id]))
            else:
                asyncio.create_task(asyncio.to_thread(self.cl.direct_send, "⚠️ No active spam sequence running.", thread_ids=[self.target_thread_id]))

    async def execute_spam_loop(self, base_text: str, delay: float):
        # 6 parallel execution workers maximizing TCP socket saturation
        concurrency_workers = 6
        
        async def worker_pipeline():
            while not self.stop_flag.is_set():
                heart = random.choice(HEART_EMOJIS)
                payload = generate_formatted_block(base_text, heart, line_count=40)
                
                if self.stop_flag.is_set():
                    break

                try:
                    # Zero console print overhead — pure raw speed transmission
                    await asyncio.to_thread(
                        self.cl.direct_send,
                        payload,
                        thread_ids=[self.target_thread_id]
                    )
                except Exception as e:
                    if "429" in str(e) or "FeedbackRequired" in str(e):
                        await asyncio.sleep(1)
                    continue

                if delay > 0 and not self.stop_flag.is_set():
                    await asyncio.sleep(delay)

        # Launch concurrent pipeline tasks
        tasks = [asyncio.create_task(worker_pipeline()) for _ in range(concurrency_workers)]
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()

async def main():
    print("[+] Initializing lightweight async Instagram client...")
    cl = Client()
    session_file = "session.json"

    if os.path.exists(session_file):
        print("[+] Loading saved session tokens...")
        cl.load_settings(session_file)
    else:
        print("[!] Error: session.json not found!")
        return

    target_thread_id = "340282366841710301281155341573245163458"
    
    bot = AsyncInstagramCommandBot(cl, target_thread_id, prefix="^")
    await bot.start_listener()

if __name__ == "__main__":
    asyncio.run(main())
