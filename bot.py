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

    async def start_listener(self):
        print(f"[+] Initializing Async API Command Listener...")

        # Seed initial messages to ignore old history
        try:
            initial_thread = await asyncio.to_thread(self.cl.direct_thread, self.target_thread_id)
            for m in initial_thread.messages[:5]:
                self.processed_message_ids.add(m.id)
            print("[+] Synced chat history. Async listener live! ⚡")
        except Exception as e:
            print(f"[!] Warning during initial sync: {e}")

        while self.is_running:
            try:
                thread = await asyncio.to_thread(self.cl.direct_thread, self.target_thread_id)
                messages = thread.messages
                
                if messages:
                    latest = messages[0]
                    msg_id = latest.id
                    msg_text = latest.text if latest.text else ""
                    
                    if msg_id not in self.processed_message_ids:
                        self.processed_message_ids.add(msg_id)
                        
                        if msg_text.startswith(self.prefix):
                            print(f"[+] Async Command Caught: {msg_text}")
                            await self.process_command(msg_text)
                
                await asyncio.sleep(0.8) # Blazing fast non-blocking poll
                
            except Exception as e:
                print(f"[!] Error in async listener loop: {e}")
                await asyncio.sleep(2)

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
                await asyncio.to_thread(self.cl.direct_send, "Usage: ^spam <text> [delay_in_seconds]", thread_ids=[self.target_thread_id])
                return
            
            delay = 0.4
            spam_text = " ".join(args)
            
            if len(args) > 1:
                try:
                    possible_delay = float(args[-1])
                    delay = max(0.3, possible_delay)
                    spam_text = " ".join(args[:-1])
                except ValueError:
                    pass

            if not spam_text:
                await asyncio.to_thread(self.cl.direct_send, "Usage: ^spam <text> [delay_in_seconds]", thread_ids=[self.target_thread_id])
                return

            await asyncio.to_thread(
                self.cl.direct_send,
                f"⚡ Async Infinite Spam Initialized | Text: '{spam_text}' | Delay: {delay}s",
                thread_ids=[self.target_thread_id]
            )

            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()

            self.active_spam_task = asyncio.create_task(self.execute_spam_loop(spam_text, delay))

        elif cmd in [f"{self.prefix}unspam", f"{self.prefix}stop"]:
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
                self.active_spam_task = None
                await asyncio.to_thread(
                    self.cl.direct_send,
                    "🛑 Active spam sequence successfully aborted via async cancellation!",
                    thread_ids=[self.target_thread_id]
                )
                print("[+] Spam task cancelled.")
            else:
                await asyncio.to_thread(
                    self.cl.direct_send,
                    "⚠️ No active spam sequence is currently running.",
                    thread_ids=[self.target_thread_id]
                )

    async def execute_spam_loop(self, base_text: str, delay: float):
        try:
            block_num = 1
            while True:
                heart = random.choice(HEART_EMOJIS)
                payload = generate_formatted_block(base_text, heart, line_count=40)
                
                await asyncio.to_thread(
                    self.cl.direct_send,
                    payload,
                    thread_ids=[self.target_thread_id]
                )
                print(f"[+] Dispatched async spam block {block_num} | Delay: {delay}s")
                block_num += 1
                
                await asyncio.sleep(delay)
                
        except asyncio.CancelledError:
            print("[!] Async spam loop was successfully cancelled.")
        except Exception as e:
            print(f"[!] Error in async spam loop: {e}")

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
