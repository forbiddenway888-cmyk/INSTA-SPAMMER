import os
import json
import time
import random
import aiohttp
import asyncio
import gc
from playwright.async_api import async_playwright

# The Phoenix Memory Bank (Stored in a mutable dict to bypass global scope errors)


HEART_EMOJIS = ["💚", "💙", "❤️", "🖤", "🤎", "💛", "💜", "🧡", "🤍", "🩶", "🩷"]
INVISIBLE_CHARS = ["\u200B", "\u200C", "\u200D", "\uFEFF"]

def generate_formatted_block(base_text: str, selected_heart: str, line_count: int = 20) -> str:
    lines = []
    current_len = 0
    
    for _ in range(line_count):
        # Pick a random invisible character to make the string hash unique
        hidden_stealth = random.choice(INVISIBLE_CHARS)
        
        # Format normally with the hidden character attached safely at the end
        line = f"{base_text} <{selected_heart}>{hidden_stealth}"
        addition = len(line) + 2  # Account for "\n\n"
        
        if current_len + addition > 950:
            break
            
        lines.append(line)
        current_len += addition
        
    return "\n\n".join(lines)


async def fetch_proxy_sources() -> list:
    # Aggregated top-tier free proxy endpoints
    sources = [
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text&timeout=5000&protocol=http",
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    
    raw_proxies = set()
    async with aiohttp.ClientSession() as session:
        for url in sources:
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        text = await response.text()
                        lines = text.strip().splitlines()
                        for line in lines:
                            cleaned = line.strip()
                            if ":" in cleaned and not cleaned.startswith("#"):
                                raw_proxies.add(cleaned)
            except Exception:
                continue
                
    return list(raw_proxies)[:150] # Test top 150 candidates for max speed

async def test_single_proxy(proxy: str, semaphore: asyncio.Semaphore) -> tuple:
    async with semaphore:
        proxy_url = f"http://{proxy}"
        # MUST test HTTPS, because Instagram uses HTTPS!
        test_url = "https://api.ipify.org?format=json" 
        start_time = time.time()
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(test_url, proxy=proxy_url, timeout=4) as resp:
                    if resp.status == 200:
                        latency = time.time() - start_time
                        return (proxy, latency, "HTTPS Verified")
        except Exception:
            pass
        return (None, float('inf'), None)

async def get_best_working_proxy() -> str:
    print("[*] Scraping fresh high-quality proxies from global public lists...", flush=True)
    proxies = await fetch_proxy_sources()
    if not proxies:
        print("[!] Warning: Proxy scraper failed to fetch IPs. Falling back to direct cloud connection.", flush=True)
        return None
        
    print(f"[+] Scraped {len(proxies)} candidates. Running concurrent speed validation tests...", flush=True)
    
    semaphore = asyncio.Semaphore(25) # Test 25 proxies simultaneously
    tasks = [test_single_proxy(p, semaphore) for p in proxies]
    results = await asyncio.gather(*tasks)
    
    valid_proxies = [r for r in results if r[0] is not None]
    if not valid_proxies:
        print("[!] Warning: All scraped proxies failed validation. Falling back.", flush=True)
        return None
        
    # Sort by lowest latency (fastest response time)
    valid_proxies.sort(key=lambda x: x[1])
    best_proxy, best_latency, country = valid_proxies[0]
    
    print(f"🎯 Best Proxy Selected! IP: {best_proxy} | Country: {country} | Latency: {round(best_latency * 1000, 2)}ms", flush=True)
    return f"http://{best_proxy}"

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
        print("[+] Starting lightweight Playwright browser engine (Direct Stealth Mode)...", flush=True)
        
        p = await async_playwright().start()
        
        self.browser = await p.chromium.launch(
            headless=True,
            ignore_default_args=["--enable-automation"], 
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--no-zygote",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-blink-features=AutomationControlled",
                "--js-flags=--max-old-space-size=384 --expose-gc"
            ]
        )
        
        context_kwargs = {
            "viewport": {"width": 1920, "height": 1080},
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        }
            
        self.context = await self.browser.new_context(**context_kwargs)
        
        # Media Blackhole
        async def block_heavy_assets(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            else:
                await route.continue_()
                
        #await self.context.route("**/*", block_heavy_assets)

        # ==========================================
        # 500 IQ VISIBILITY & WEBDRIVER SPOOF
        # ==========================================
        await self.context.add_init_script("""
            // 1. Erase the headless bot flag
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // 2. Fake the Chrome runtime object
            window.chrome = { runtime: {} };
            
            // 3. Fake browser plugins so it doesn't look like a blank cloud container
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            
            // 4. Force visibility
            Object.defineProperty(document, 'visibilityState', { get: () => 'visible' });
            Object.defineProperty(document, 'hidden', { get: () => false });
            Object.defineProperty(document, 'hasFocus', { get: () => true });
        """)
        
        await self.load_cookies()
        
        self.page = await self.context.new_page()
        
        # STEP 1: Warm up session on Instagram's main entry to pass edge security checks
        print("[*] Warming up session on Instagram main entry...", flush=True)
        await self.page.goto("https://www.instagram.com/", timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # STEP 2: Now navigate directly to the chat thread with established session context
        print("[+] Navigating directly to Instagram chat thread...", flush=True)
        await self.page.goto(f"https://www.instagram.com/direct/t/{self.target_thread_id}/", timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        # STEP 2: Now navigate directly to the chat thread with established session context
        print("[+] Navigating directly to Instagram chat thread...", flush=True)
        await self.page.goto(f"https://www.instagram.com/direct/t/{self.target_thread_id}/", timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        
        # 200 IQ: ASSASSINATE THE SPLASH SCREEN OVERLAY
        try:
            print("[*] Stripping Instagram splash screen overlays...", flush=True)
            await self.page.evaluate("""
                const splash = document.getElementById('splash-screen');
                if (splash) splash.remove();
                
                // Rip out any other blocking overlay divs
                document.querySelectorAll('div[role="presentation"], div[role="dialog"]').forEach(el => {
                    if (el.style.position === 'fixed') el.remove();
                });
            """)
        except Exception:
            pass

        # 200 IQ: SPA WAKE-UP & ESCAPE NUKE (Kills hidden modals instantly)
        try:
            await self.page.mouse.click(500, 500)
            await self.page.keyboard.press("Escape") 
            await asyncio.sleep(2)
        except Exception:
            pass

        # Check if Instagram bounced us back to home (expired cookies)
        if "accounts/login" in self.page.url or self.page.url == "https://www.instagram.com/":
            print("[!] CRITICAL: Session cookies expired! Instagram bounced the bot back to home/login.", flush=True)
            print("[!] Please update your session.json with fresh cookies.", flush=True)
        
        for popup_text in ["Not Now", "Not now", "Cancel"]:
            try:
                btn = self.page.get_by_role("button", name=popup_text)
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    print(f"[+] Dismissed popup: '{popup_text}'", flush=True)
            except Exception:
                pass

        try:
            print("[+] Waiting for chat input box anchor...", flush=True)
            # The absolute most generic React textbox selector
            await self.page.wait_for_selector("div[role='textbox']", timeout=30000)
            print("[+] Chat thread fully mounted and ready! 🎯", flush=True)
        except Exception as e:
            current_url = self.page.url
            page_title = await self.page.title()
            
            # 200 IQ DOM X-RAY: Scrape ONLY the body HTML to see if React is rendering the UI
            try:
                body_html = await self.page.evaluate("document.body.innerHTML")
                print(f"\n[🔍 200 IQ X-RAY] Body HTML Dump: {body_html[:1500]}\n", flush=True)
            except:
                pass
                
            print(f"[!] CLOUD BLOCK DETECTED! Current URL: {current_url} | Title: {page_title}", flush=True)
            raise e
            
        await self.sync_initial_messages()
        
        # ==========================================
        # 500 IQ PHOENIX AUTO-RESUME (DISK BACKED)
        # ==========================================
        saved_state = None
        if os.path.exists("memory_bank.txt"):
            try:
                with open("memory_bank.txt", "r") as f:
                    saved_state = f.read().strip()
            except Exception:
                pass

        if saved_state:
            print("[*] Disk Memory Bank active! Waiting 6s for full DOM stabilization...", flush=True)
            await asyncio.sleep(6) 
            print(f"[*] Firing saved payload from disk: {saved_state}", flush=True)
            asyncio.create_task(self.process_command(saved_state))
            
        # SINGLE, UNIFIED POLLING LOOP (THE END OF START)
        await self.poll_loop()

    async def blast_payload(self, text: str):
        try:
            # Broadened selector to match start()
            box = self.page.locator("div[contenteditable='true'], div[aria-label='Message'], p.xdj266r").first
            
            # Ultra-lightweight injection: avoids heavy range selection DOM thrashing
            await box.evaluate(
                """(element, payloadText) => {
                    element.focus();
                    element.textContent = payloadText;
                    element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: payloadText }));
                }""",
                arg=text
            )
            
            # Clean browser-level Enter dispatch
            await self.page.keyboard.press("Enter")
            return True
        except Exception:
            return False
            

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

    async def save_cookies_backup(self):
        try:
            cookies = await self.context.cookies()
            cookies_dict = {c['name']: c['value'] for c in cookies}
            data = {"cookies": cookies_dict}
            
            with open("session.json", "w") as f:
                json.dump(data, f, indent=2)
            print("[+] Session cookies successfully auto-backed up to disk! 💾", flush=True)
        except Exception as e:
            print(f"[!] Cookie backup error: {e}", flush=True)
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
        last_heartbeat_time = time.time()
        last_cookie_backup_time = time.time()

        while self.is_running:
            try:
                current_time = time.time()
                
                # 500 IQ COOKIE AUTO-BACKUP: Backup session tokens every 30 minutes (1800 seconds)
                if current_time - last_cookie_backup_time > 1800:
                    await self.save_cookies_backup()
                    last_cookie_backup_time = time.time()
                
                # 500 IQ GHOST HEARTBEAT: Fire every 2.5 minutes (150 seconds)
                if current_time - last_heartbeat_time > 150:
                    is_spamming = hasattr(self, 'active_spam_task') and self.active_spam_task and not self.active_spam_task.done()
                    
                    if not is_spamming:
                        try:
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
                                b.setAttribute("data-bot-processed", "true");
                            }}
                        }});
                        return found;
                    }}
                ''')

                for cmd_text in new_commands:
                    lines = [l.strip() for l in cmd_text.splitlines() if l.strip()]
                    for line in lines:
                        if line.startswith(self.prefix):
                            print(f"[+] Instant Command Caught: {line}", flush=True)
                            asyncio.create_task(self.process_command(line))
                            break
                            
            except Exception as e:
                error_msg = str(e).lower()
                
                if "closed" in error_msg or "pipe" in error_msg or "target crashed" in error_msg:
                    print("\n[!] FATAL OS RAM CRASH DETECTED! Browser assassinated.", flush=True)
                    print("[*] Initiating Phoenix Protocol: Wiping dead engine... 🦅", flush=True)
                    
                    self.is_running = False
                    self.stop_flag.set() 
                    if hasattr(self, 'active_spam_task') and self.active_spam_task and not self.active_spam_task.done():
                        self.active_spam_task.cancel()
                        
                    break 
                
                print(f"[!] Polling error: {e}", flush=True)
                await asyncio.sleep(2) 
            
            await asyncio.sleep(0.8)

    async def process_command(self, full_text: str):
        parts = full_text.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == f"{self.prefix}ping":
            try:
                start_t = time.time()
                await self.send_message("Pong! 🏓 Live Latency: Calculating... | Zero-Latency Engine Active! ⚡")
                end_t = time.time()
                
                latency_ms = round((end_t - start_t) * 1000, 2)
                print(f"[+] Ping executed in {latency_ms}ms", flush=True)
            except Exception as e:
                print(f"[!] Ping error: {e}", flush=True)

        elif cmd == f"{self.prefix}spam":
            # 💾 SAVE TO DISK: Survives total server reboots
            with open("memory_bank.txt", "w") as f:
                f.write(full_text)
            
            if not args:
                await self.send_message("Usage: ^spam <text> [delay]")
                return
            
            delay = 0.24
            spam_text = " ".join(args)
            
            if len(args) > 1:
                try:
                    possible_delay = float(args[-1])
                    delay = max(0.05, possible_delay) 
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
            # 🗑️ WIPE FROM DISK: Stops the auto-resume permanently
            if os.path.exists("memory_bank.txt"):
                os.remove("memory_bank.txt")
            
            self.stop_flag.set()
            if hasattr(self, 'active_spam_task') and self.active_spam_task and not self.active_spam_task.done():
                self.active_spam_task.cancel()
                
            await self.send_message("🛑 Spam engine halted. Memory bank wiped from disk.")
            print("[+] Unspam executed. Engine returning to idle.", flush=True)
            

    async def execute_spam_loop(self, base_text: str, delay: float):
        try:
            print("[+] Humanized Jittered Spam Loop Active... ⚡", flush=True)
            safe_delay = max(0.05, delay)
            msg_count = 0
            
            while not self.stop_flag.is_set():
                heart = random.choice(HEART_EMOJIS)
                payload = generate_formatted_block(base_text, heart, line_count=25)
                
                if self.stop_flag.is_set():
                    break

                try:
                    success = await self.blast_payload(payload)
                    if not success:
                        # If textbox dropped out momentarily, wait a tiny bit for re-anchor
                        await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"[!] Minor blast stutter: {e}", flush=True)
                
                msg_count += 1
                if msg_count % 50 == 0:
                    gc.collect()
                    try:
                        await self.page.evaluate("window.gc && window.gc();")
                    except Exception:
                        pass
                
                if not self.stop_flag.is_set():
                    # HUMANIZING JITTER: Varies the sleep cadence organically to evade machine patterns
                    jittered_delay = random.uniform(safe_delay, safe_delay + 0.02)
                    await asyncio.sleep(jittered_delay)
                    
        except asyncio.CancelledError:
            print("[+] Spam loop gracefully cancelled.", flush=True)
        except Exception as e:
            print(f"\n[!] FATAL SPAM LOOP ERROR: {e}\n", flush=True)
            
async def main():
    print("🚀 INITIALIZING IMMORTAL BOT ENGINE...", flush=True)
    while True:
        try:
            bot = PlaywrightInstagramBot("3678408248973250") 
            await bot.start()
        except Exception as e:
            print(f"\n[!] ENGINE CRASHED: {e}\n", flush=True)
            
        print("[*] Resting 5 seconds before Phoenix reboot...", flush=True)
        await asyncio.sleep(2)
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[+] Script manually stopped by user.")
