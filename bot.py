import os
import json
import time
import random
import asyncio
from playwright.async_api import async_playwright

HEART_EMOJIS = ["💚", "💙", "❤️", "🖤", "🤎", "💛", "💜", "🧡", "🤍", "🩶", "🩷"]

def generate_formatted_block(base_text: str, selected_heart: str, line_count: int = 15) -> str:
    lines = [f"{base_text} <{selected_heart}>" for _ in range(line_count)]
    return "\n".join(lines)

class PlaywrightInstagramBot:
    def __init__(self, target_thread_id: str, prefix: str = "^"):
        self.target_thread_id = target_thread_id
        self.prefix = prefix
        self.is_running = True
        self.processed_message_texts = set()
        self.active_spam_task = None
        self.stop_flag = asyncio.Event()
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        print("[+] Starting lightweight Playwright browser engine...", flush=True)
        p = await async_playwright().start()
        
        self.browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--no-zygote",
                "--disable-extensions"
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 800, "height": 600},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        await self.load_cookies()
        
        self.page = await self.context.new_page()
        
        # Block images, stylesheets, and fonts to reduce resource and data usage to minimum
        await self.page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
        
        print("[+] Navigating directly to Instagram chat thread...", flush=True)
        await self.page.goto(f"https://www.instagram.com/direct/t/{self.target_thread_id}/", timeout=60000)
        await asyncio.sleep(6)
        
        # Check if Instagram redirected to login
        current_url = self.page.url
        print(f"[+] Current Page URL: {current_url}", flush=True)
        if "login" in current_url or "accounts" in current_url:
            print("[!] Warning: Instagram redirected to login/checkpoint. Session cookies may need to be refreshed.", flush=True)
        
        await self.sync_initial_messages()
        await self.poll_loop()

    async def load_cookies(self):
        session_file = "session.json"
        if not os.path.exists(session_file):
            print(f"[!] Error: {session_file} not found!", flush=True)
            return
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
            
            raw_cookies = data.get("cookies", {})
            cookies_list = []
            for name, value in raw_cookies.items():
                cookies_list.append({
                    "name": name,
                    "value": str(value),
                    "domain": ".instagram.com",
                    "path": "/"
                })
            if cookies_list:
                await self.context.add_cookies(cookies_list)
                print("[+] Session cookies successfully injected into browser context!", flush=True)
        except Exception as e:
            print(f"[!] Cookie load error: {e}", flush=True)

    async def sync_initial_messages(self):
        try:
            print("[+] Syncing existing chat messages...", flush=True)
            await self.page.wait_for_selector('div[role="row"]', timeout=15000)
            messages = await self.page.locator('div[role="row"]').all_inner_texts()
            for m in messages[-10:]:
                self.processed_message_texts.add(m.strip())
            print("[+] Chat history synced. Web automation polling active! ⚡", flush=True)
        except Exception as e:
            print(f"[!] Warning during initial sync: {e}", flush=True)

    async def send_message(self, text: str):
        try:
            input_box = self.page.locator('div[contenteditable="true"][aria-label="Message"]')
            await input_box.click()
            await input_box.fill(text)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"[!] Send message error: {e}", flush=True)

    async def poll_loop(self):
        while self.is_running:
            try:
                message_elements = self.page.locator('div[role="row"]')
                count = await message_elements.count()
                if count > 0:
                    last_el = message_elements.nth(count - 1)
                    full_text = await last_el.inner_text()
                    cleaned_text = full_text.strip()
                    
                    if cleaned_text and cleaned_text not in self.processed_message_texts:
                        self.processed_message_texts.add(cleaned_text)
                        if cleaned_text.startswith(self.prefix):
                            print(f"[+] Instant Command Caught: {cleaned_text}", flush=True)
                            asyncio.create_task(self.process_command(cleaned_text))
            except Exception:
                pass
            
            await asyncio.sleep(0.4)

    async def process_command(self, full_text: str):
        parts = full_text.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == f"{self.prefix}ping":
            start_t = time.time()
            await self.send_message("Pong! 🏓 Bot active via Web Automation!")
            end_t = time.time()
            latency = round((end_t - start_t) * 1000, 2)
            print(f"[+] Ping executed in {latency}ms", flush=True)

        elif cmd == f"{self.prefix}spam":
            if not args:
                await self.send_message("Usage: ^spam <text> [delay]")
                return
            
            delay = 0.5
            spam_text = " ".join(args)
            if len(args) > 1:
                try:
                    possible_delay = float(args[-1])
                    delay = max(0.3, possible_delay)
                    spam_text = " ".join(args[:-1])
                except ValueError:
                    pass

            self.stop_flag.set()
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()

            self.stop_flag.clear()
            await self.send_message(f"⚡ Spam Active | Delay: {delay}s")
            self.active_spam_task = asyncio.create_task(self.execute_spam_loop(spam_text, delay))

        elif cmd in [f"{self.prefix}unspam", f"{self.prefix}stop"]:
            self.stop_flag.set()
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
                self.active_spam_task = None
                await self.send_message("🛑 Spam aborted successfully!")
            else:
                await self.send_message("⚠️ No active spam sequence running.")

    async def execute_spam_loop(self, base_text: str, delay: float):
        try:
            while not self.stop_flag.is_set():
                heart = random.choice(HEART_EMOJIS)
                payload = generate_formatted_block(base_text, heart, line_count=15)
                
                if self.stop_flag.is_set():
                    break

                await self.send_message(payload)
                
                if not self.stop_flag.is_set():
                    await asyncio.sleep(delay)
        except asyncio.CancelledError:
            print("[!] Spam loop cancelled.", flush=True)

async def main():
    target_thread_id = "340282366841710301281155341573245163458"
    bot = PlaywrightInstagramBot(target_thread_id, prefix="^")
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
