import os
import random
import asyncio
from playwright.async_api import async_playwright

HEART_EMOJIS = ["💚", "💙", "❤️", "🖤", "🤎", "💛", "💜", "🧡", "🤍", "🩶", "🩷"]

def generate_formatted_block(base_text: str, selected_heart: str, line_count: int = 40) -> str:
    lines = [f"{base_text} <{selected_heart}>" for _ in range(line_count)]
    return "\n\n".join(lines)

class InstagramCommandBot:
    def __init__(self, page, owner_username: str, prefix: str = "^"):
        self.page = page
        self.owner_username = owner_username.lower().strip("@")
        self.prefix = prefix
        self.is_running = True
        self.is_ready = False
        self.sent_by_bot = set()
        self.recent_commands = set()
        self.active_spam_task = None  # Track running spam task for cancellation

    async def start_listener(self):
        print(f"[+] Initializing 200 IQ Event-Driven MutationObserver for @{self.owner_username}...")

        async def handle_js_message(source, text):
            # Drop everything until the startup grace period finishes
            if not self.is_ready:
                return

            text = text.strip()
            if not text.startswith(self.prefix):
                return
            
            if text in self.recent_commands:
                return
            
            if text in self.sent_by_bot:
                return

            self.recent_commands.add(text)
            asyncio.create_task(self._clear_recent(text))

            print(f"[+] Event-Driven Command Caught: {text}")
            await self.process_command(self.owner_username, text)

        await self.page.expose_binding("pyOnNewMessage", handle_js_message)

        # Inject MutationObserver
        await self.page.evaluate("""() => {
            if (window.__ig_observer_active) return;
            window.__ig_observer_active = true;

            const observer = new MutationObserver((mutations) => {
                for (let mutation of mutations) {
                    for (let node of mutation.addedNodes) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const spans = node.querySelectorAll("span[dir='auto']");
                            spans.forEach(span => {
                                const txt = span.textContent ? span.textContent.trim() : "";
                                if (txt.startsWith("^")) {
                                    window.pyOnNewMessage(txt);
                                }
                            });
                            if (node.matches && node.matches("span[dir='auto']")) {
                                const txt = node.textContent ? node.textContent.trim() : "";
                                if (txt.startsWith("^")) {
                                    window.pyOnNewMessage(txt);
                                }
                            }
                        }
                    }
                }
            });

            const targetArea = document.querySelector("div[role='main']") || document.body;
            observer.observe(targetArea, { childList: true, subtree: true });
        }""")

        print("[+] Settling chat history (ignoring old messages)...")
        # Wait 3.5 seconds for Instagram to finish loading previous chat nodes into DOM
        await asyncio.sleep(3.5)
        
        self.is_ready = True
        print("[+] Bot is now fully LIVE and listening for brand new commands only! ⚡")
        
        while self.is_running:
            await asyncio.sleep(1)

    async def _clear_recent(self, text: str):
        await asyncio.sleep(3)
        self.recent_commands.discard(text)

    async def send_chat_message(self, text: str):
        try:
            self.sent_by_bot.add(text)
            box = self.page.locator("div[contenteditable='true'][role='textbox'], p.xdj266r").first
            await box.click()
            
            await box.evaluate(
                """(el, val) => {
                    el.focus();
                    el.textContent = val;
                    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: val }));
                }""",
                text
            )
            await self.page.keyboard.press("Enter")
        except Exception as e:
            print(f"[!] Failed to send message response: {e}")

    async def process_command(self, sender: str, full_text: str):
        print(f"[DEBUG] process_command triggered with text: '{full_text}'")
        
        parts = full_text.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        print(f"[!] Command parsed -> Cmd: '{cmd}' | Args: {args}")

        if sender != self.owner_username and sender != "unknown":
            print(f"[!] Access Denied for @{sender}. Unauthorized attempt.")
            await self.send_chat_message(f"Access denied @{sender}! Forbid baap ka bot use krega kya lawde? 💀")
            return

        if cmd == f"{self.prefix}ping":
            start_time = asyncio.get_event_loop().time()
            await self.page.evaluate("performance.now()")
            end_time = asyncio.get_event_loop().time()
            
            latency_ms = round((end_time - start_time) * 1000, 2)
            await self.send_chat_message(f"Pong! 🏓 Live Network Latency: {latency_ms}ms | Zero-latency active ⚡")

        elif cmd == f"{self.prefix}spam":
            if not args:
                await self.send_chat_message("Usage: ^spam <text> [delay_in_seconds]")
                return
            
            delay = 0.28
            spam_text = " ".join(args)
            
            if len(args) > 1:
                try:
                    possible_delay = float(args[-1])
                    delay = possible_delay
                    spam_text = " ".join(args[:-1])
                except ValueError:
                    pass

            if not spam_text:
                await self.send_chat_message("Usage: ^spam <text> [delay_in_seconds]")
                return

            await self.send_chat_message(f"⚡ Infinite spam initialized | Text: '{spam_text}' | Delay: {delay}s")
            
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
            
            self.active_spam_task = asyncio.create_task(self.execute_spam_loop(spam_text, delay))

        elif cmd in [f"{self.prefix}unspam", f"{self.prefix}stop"]:
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
                self.active_spam_task = None
                await self.send_chat_message("🛑 Active spam sequence successfully aborted!")
            else:
                await self.send_chat_message("⚠️ No active spam sequence is currently running.")

     


   

    async def execute_spam_loop(self, base_text: str, delay: float):
        try:
            box = self.page.locator("div[contenteditable='true'][role='textbox'], p.xdj266r").first
            await box.click()

            block_num = 1
            while True:
                heart = random.choice(HEART_EMOJIS)
                payload = generate_formatted_block(base_text, heart, line_count=40)
                
                self.sent_by_bot.add(payload)

                await box.evaluate(
                    """(el, text) => {
                        el.focus();
                        el.textContent = text;
                        el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
                    }""",
                    payload
                )
                
                await box.press("Enter")
                print(f"[+] Dispatched infinite spam block {block_num} | Delay: {delay}s")
                block_num += 1
                
                await asyncio.sleep(delay)
                
        except asyncio.CancelledError:
            print("[!] Spam sequence was successfully aborted.")
            # Removed the duplicate self.send_chat_message here to prevent delayed ghost messages
        except Exception as e:
            print(f"[!] Error in spam loop execution: {e}")

    async def main():
    user_data_dir = os.path.join(os.path.expanduser("~"), "playwright_instagram_profile")
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None

   async with async_playwright() as p:
        print("Launching browser engine...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=is_railway,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )

        page = context.pages[0] if context.pages else await context.new_page()
        
        target_url = os.getenv("TARGET_URL", "https://www.instagram.com/direct/t/3678408248973250/")
        owner = os.getenv("BOT_OWNER", "forrbidhu")
        
        print(f"Opening target thread: {target_url}")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

        if not is_railway:
            input("\nOnce logged in and thread is visible, press ENTER to activate command bot...")

        bot = InstagramCommandBot(page, owner_username=owner, prefix="^")
        await bot.start_listener()

if __name__ == "__main__":
    asyncio.run(main())
