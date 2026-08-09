import os
import json
import time
import random
import asyncio
import gc
from playwright.async_api import async_playwright

# The Phoenix Memory Bank
ACTIVE_SPAM_STATE = None

HEART_EMOJIS = ["💚", "💙", "❤️", "🖤", "🤎", "💛", "💜", "🧡", "🤍", "🩶", "🩷"]

def generate_max_payload(base_text: str, selected_heart: str) -> str:
    # Instagram's absolute max DM length is 1000 characters. 
    # We mathematically target ~950 to ensure max screen space without hitting the 400 error.
    line = f"{base_text} <{selected_heart}>\n"
    line_len = len(line)
    
    if line_len >= 950:
        return line[:950]
    
    repeats = 950 // line_len
    return (line * repeats).strip()

class PlaywrightInstagramBot:
    def __init__(self, target_thread_id: str, prefix: str = "^"):
        self.target_thread_id = target_thread_id
        self.prefix = prefix
        self.is_running = True
        self.processed_message_hashes = set()
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
                "--disable-extensions",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                # 500 IQ: Cap RAM at 250MB AND expose the native C++ Garbage Collector!
                "--js-flags=--max-old-space-size=250 --expose-gc"
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 800, "height": 600},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        # ==========================================
        # 500 IQ INVINCIBILITY: The Media Blackhole
        # ==========================================
        async def block_heavy_assets(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            else:
                await route.continue_()
                
        # Apply the blackhole to the entire browser context
        await self.context.route("**/*", block_heavy_assets)

        # ==========================================
        # 500 IQ VISIBILITY SPOOF
        # ==========================================
        await self.context.add_init_script("""
            Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
            Object.defineProperty(document, 'hidden', { get: () => false });
            Object.defineProperty(document, 'hasFocus', { get: () => true });
        """)
        
        await self.load_cookies()
        
        self.page = await self.context.new_page()
        
        print("[+] Navigating directly to Instagram chat thread...", flush=True)
        await self.page.goto(f"https://www.instagram.com/direct/t/{self.target_thread_id}/", timeout=60000)
        await asyncio.sleep(4)
        
        # 1. Automatically dismiss blocking Instagram popups ("Not Now", "Cancel")
        for popup_text in ["Not Now", "Not now", "Cancel"]:
            try:
                btn = self.page.get_by_role("button", name=popup_text)
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    print(f"[+] Dismissed popup: '{popup_text}'", flush=True)
            except Exception:
                pass

        # 2. Anchor on the message box (proves the thread is loaded)
        try:
            print("[+] Waiting for chat input box anchor...", flush=True)
            await self.page.wait_for_selector("div[contenteditable='true'][role='textbox'], p.xdj266r", timeout=30000)
            print("[+] Chat thread fully mounted and ready! 🎯", flush=True)
        except Exception as e:
            print(f"[!] Warning: Chat input anchor check timed out: {e}", flush=True)
            
        # Sync initial messages ONCE
        await self.sync_initial_messages()
        
        # ==========================================
        # 200 IQ ZERO-LAG AUTO-RESUME
        # ==========================================
        global ACTIVE_SPAM_STATE
        if ACTIVE_SPAM_STATE:
            print(f"[*] Phoenix Memory Bank active! INSTANT Resume: {ACTIVE_SPAM_STATE}", flush=True)
            # The exact millisecond the chat is synced, it fires the saved command!
            asyncio.create_task(self.process_command(ACTIVE_SPAM_STATE))
            
        await self.poll_loop()

    async def blast_payload(self, text: str):
        try:
            box = self.page.locator("div[contenteditable='true'][role='textbox'], p.xdj266r").first
            await box.evaluate(
                """(element, text) => {
                    element.focus();
                    element.textContent = text;
                    element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
                }""",
                arg=text
            )
            # Programmatic Enter bypasses UI limits
            await self.page.keyboard.press("Enter")
        except Exception:
            pass
            

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
            # Inject JS to invisibly tag all current messages as 'processed'
            await self.page.evaluate('''
                () => {
                    const bubbles = document.querySelectorAll('div[dir="auto"]');
                    bubbles.forEach(b => {
                        if (b.innerText.trim().includes("^")) {
                            b.setAttribute("data-bot-processed", "true");
                        }
                    });
                }
            ''')
            print("[+] Synced existing chat history. JS tagging active! ⚡", flush=True)
        except Exception as e:
            print(f"[!] Warning during initial sync: {e}", flush=True)

    async def send_message(self, text: str):
        try:
            # Use the robust selector from your script
            box = self.page.locator("div[contenteditable='true'][role='textbox'], p.xdj266r").first
            
            # Direct DOM value injection coupled with forced React event dispatch
            await box.evaluate(
                """(element, text) => {
                    element.focus();
                    element.textContent = text;
                    element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
                }""",
                arg=text
            )
            
            # Instant programmatic keypress for submission
            await self.page.keyboard.press("Enter")
            
            # Absolute maximum threshold before Meta's server drops packets (from your script)
            await asyncio.sleep(0.28)
        except Exception as e:
            print(f"[!] Send message error: {e}", flush=True)

    async def poll_loop(self):
        print("[+] Hyper-speed JS polling loop active! Listening for commands...", flush=True)
        # Track the last time we sent a heartbeat
        last_heartbeat_time = time.time()

        while self.is_running:
            try:
                current_time = time.time()
                
                # 500 IQ GHOST HEARTBEAT: Fire every 2.5 minutes (150 seconds)
                if current_time - last_heartbeat_time > 150:
                    is_spamming = hasattr(self, 'active_spam_task') and self.active_spam_task and not self.active_spam_task.done()
                    
                    if not is_spamming:
                        try:
                            # Actually click the text box so Meta's React engine registers human presence
                            box = self.page.locator("div[contenteditable='true'][role='textbox'], p.xdj266r").first
                            await box.click(timeout=2000)
                        except Exception:
                            pass
                        
                    last_heartbeat_time = time.time()

                # Ask the browser to find any new message bubble that hasn't been tagged yet
                new_commands = await self.page.evaluate(f'''
                    () => {{
                        const bubbles = document.querySelectorAll('div[dir="auto"]');
                        const found = [];
                        bubbles.forEach(b => {{
                            const text = b.innerText.trim();
                            if (text.includes("{self.prefix}") && !b.hasAttribute("data-bot-processed")) {{
                                found.push(text);
                                b.setAttribute("data-bot-processed", "true"); // Tag it instantly
                            }}
                        }});
                        return found;
                    }}
                ''')

                # Process any newly found commands
                for cmd_text in new_commands:
                    lines = [l.strip() for l in cmd_text.splitlines() if l.strip()]
                    for line in lines:
                        if line.startswith(self.prefix):
                            print(f"[+] Instant Command Caught: {line}", flush=True)
                            asyncio.create_task(self.process_command(line))
                            break
                            
            except Exception as e:
                error_msg = str(e).lower()
                
                # 500 IQ MOVE: Detect the exact moment the OS kills the browser
                if "closed" in error_msg or "pipe" in error_msg or "target crashed" in error_msg:
                    print("\n[!] FATAL OS RAM CRASH DETECTED! Browser assassinated.", flush=True)
                    print("[*] Initiating Phoenix Protocol: Wiping dead engine... 🦅", flush=True)
                    
                    # DOUBLE-TAP THE ZOMBIE: Explicitly cancel the active spam loop!
                    self.is_running = False
                    self.stop_flag.set() 
                    if hasattr(self, 'active_spam_task') and self.active_spam_task and not self.active_spam_task.done():
                        self.active_spam_task.cancel()
                        
                    break  # Shatter the dead loop so we can restart cleanly!
                
                print(f"[!] Polling error: {e}", flush=True)
                await asyncio.sleep(2) 
            
            await asyncio.sleep(0.8)

    async def process_command(self, full_text: str):
        # 500 IQ FIX: Declare the global at the absolute top of the function!
        global ACTIVE_SPAM_STATE
        parts = full_text.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == f"{self.prefix}ping":
            try:
                start_t = time.time()
                # Measure exact round-trip dispatch latency to the browser & socket
                await self.send_message("Pong! 🏓 Live Latency: Calculating... | Zero-Latency Engine Active! ⚡")
                end_t = time.time()
                
                latency_ms = round((end_t - start_t) * 1000, 2)
                print(f"[+] Ping executed in {latency_ms}ms", flush=True)
            except Exception as e:
                print(f"[!] Ping error: {e}", flush=True)

        elif cmd == f"{self.prefix}spam":
            # Just directly assign it now, Python already knows it's global!
            ACTIVE_SPAM_STATE = full_text  
            
            if not args:
                await self.send_message("Usage: ^spam <text> [delay]")
                return
            
            # 0.28s is the theoretical Meta packet-drop limit based on your local script
            delay = 0.25
            spam_text = " ".join(args)
            
            if len(args) > 1:
                try:
                    possible_delay = float(args[-1])
                    # Absolute hard limit at 0.25s to prevent immediate websocket disconnects
                    delay = max(0.25, possible_delay) 
                    spam_text = " ".join(args[:-1])
                except ValueError:
                    pass

            self.stop_flag.set()
            if self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()

            self.stop_flag.clear()
            await self.send_message(f"⚡ MAX-SPEED Engine Active | Auto-Expanding Payload | Delay: {delay}s")
            
            self.active_spam_task = asyncio.create_task(self.execute_spam_loop(spam_text, delay))

        elif cmd == f"{self.prefix}unspam":
            # Wipe the memory bank
            ACTIVE_SPAM_STATE = None  
            
            # Trigger the stop flag and kill the active task
            self.stop_flag.set()
            if hasattr(self, 'active_spam_task') and self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
                
            await self.send_message("🛑 Spam engine halted. Memory bank wiped.")
            print("[+] Unspam executed. Engine returning to idle.", flush=True)
            

    async def execute_spam_loop(self, base_text: str, delay: float):
        try:
            safe_delay = max(0.25, delay)
            msg_count = 0
            
            while not self.stop_flag.is_set():
                heart = random.choice(HEART_EMOJIS)
                payload = generate_max_payload(base_text, heart)
                
                if self.stop_flag.is_set():
                    break

                # ==========================================
                # 500 IQ TANK ARMOR: Try/Except the blast!
                # If Instagram UI lags, it won't shatter the loop.
                # ==========================================
                try:
                    await self.blast_payload(payload)
                except Exception as e:
                    print(f"[!] Minor DOM stutter (ignored, firing next): {e}", flush=True)
                
                # Active Memory Management: Force Python to empty RAM
                msg_count += 1
                if msg_count % 30 == 0:
                    gc.collect()
                    try:
                        await self.page.evaluate("window.gc && window.gc();")
                    except Exception:
                        pass
                
                if not self.stop_flag.is_set():
                    await asyncio.sleep(safe_delay)
                    
        except asyncio.CancelledError:
            print("[+] Spam loop gracefully cancelled.", flush=True)
        except Exception as e:
            # THIS exposes any fatal logic errors so it NEVER dies silently again
            print(f"\n[!] FATAL SPAM LOOP ERROR: {e}\n", flush=True)
            
async def main():
    print("🚀 INITIALIZING IMMORTAL BOT ENGINE...", flush=True)
    while True:
        try:
            bot = PlaywrightInstagramBot("3678408248973250") 
            await bot.start()
        except Exception:
            pass # Mute the death error so it doesn't clutter the terminal
        
        # 200 IQ ZERO-LAG REBOOT: No sleep. CPU immediately builds a new browser.
        print("[*] Phoenix Protocol executing INSTANT reboot...", flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[+] Script manually stopped by user.")
