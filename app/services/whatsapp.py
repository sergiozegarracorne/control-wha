import asyncio
import base64
import os
from playwright.async_api import async_playwright, Page, BrowserContext
from app.core import config
from app.services.queue_manager import queue_manager

class WhatsAppService:
    _instance = None
    playwright = None
    browser = None
    context = None
    page = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WhatsAppService, cls).__new__(cls)
        return cls._instance

    async def start(self, on_browser_close_callback=None):
        if self.page:
            return

        self.on_browser_close_callback = on_browser_close_callback
        print("Starting Playwright Service (Persistent Mode)...")
        self.playwright = await async_playwright().start()
        
        # Fixed User Agent
        REAL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        launch_args = {
            "headless": config.HEADLESS,
            "user_agent": REAL_USER_AGENT,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"],
            "viewport": {"width": 1280, "height": 800}
        }

        # Custom Executable Path
        if config.BROWSER_EXECUTABLE_PATH:
            print(f"Using custom executable: {config.BROWSER_EXECUTABLE_PATH}")
            launch_args["executable_path"] = config.BROWSER_EXECUTABLE_PATH
        
        elif config.BROWSER_CHANNEL:
             launch_args["channel"] = config.BROWSER_CHANNEL

        print(f"Loading persistent context from: {config.USER_DATA_DIR}")
        
        # We use launch_persistent_context which automatically handles storage/cookies/indexedDB
        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=config.USER_DATA_DIR,
                **launch_args
            )
            # Monitor Browser Closure
            self.context.on("close", lambda: asyncio.create_task(self.on_context_closed()))

        except Exception as e:
            print(f"Error launching persistent context: {e}")
            # Fallback if channel fails or locked?
            raise e

        # Get the first page or create new
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        
        # Start Queue Consumer Background Task
        asyncio.create_task(self.process_queue_loop())

        try:
            print(f"Navigating to {config.WHATSAPP_URL}")
            await self.page.goto(config.WHATSAPP_URL, timeout=60000)
        except Exception as e:
            print(f"Error navigating: {e}")

    async def process_queue_loop(self):
        """Background task to process messages from SQLite Queue sequentially."""
        print("🚀 Queue Consumer Started: Waiting for messages...")
        
        while True:
            try:
                # 1. Get next pending message
                msg = queue_manager.get_next_pending()
                
                if msg:
                    print(f"🔄 Processing Message ID {msg['id']} for {msg['phone']}...")
                    
                    try:
                        # 1.5 Check for Duplicates (Anti-Spam)
                        # Only if threshold > 0 (0 means disabled)
                        if config.SIMILARITY_THRESHOLD > 0:
                            threshold = config.SIMILARITY_THRESHOLD / 100.0
                            is_dup, reason = queue_manager.check_duplicate(msg['phone'], msg['message'], exclude_id=msg['id'], threshold=threshold)
                            
                            if is_dup:
                                print(f"🛑 SKIP Message ID {msg['id']}: {reason}")
                                queue_manager.mark_completed(msg['id'], status='DUPLICATE', error=reason)
                                continue

                        # 2. Add random delay to look human and avoid race conditions
                        await asyncio.sleep(2) 

                        # 3. Send Message
                        await self.send_message(msg['phone'], msg['message'], msg.get('image_path'))
                        
                        # 4. Mark as SENT
                        queue_manager.mark_completed(msg['id'], status='SENT')
                        print(f"✅ Message ID {msg['id']} SENT successfully.")
                        
                        # Throttle: Wait a bit more after success
                        await asyncio.sleep(3) 

                    except Exception as e:
                        print(f"❌ Error sending Message ID {msg['id']}: {e}")
                        queue_manager.mark_completed(msg['id'], status='ERROR', error=str(e))
                else:
                    # No messages, wait before polling again
                    await asyncio.sleep(3)

            except Exception as e:
                print(f"⚠️ Safety Loop Error: {e}")
                await asyncio.sleep(5)

    async def get_status(self):
        if not self.page:
            return "not_initialized"

        # Check for Chat List (Logged in)
        try:
            # Quick check (1s)
            await self.page.wait_for_selector("#pane-side", timeout=1000)
            return "connected"
        except:
            pass

        # Check for QR Canvas
        try:
            await self.page.wait_for_selector("canvas", timeout=1000)
            return "waiting_qr"
        except:
            pass

        return "loading"

    async def get_qr(self):
        if not self.page:
            return None
        
        try:
            # Wait a bit for canvas to render
            element = await self.page.wait_for_selector("canvas", timeout=5000)
            if element:
                png_bytes = await element.screenshot()
                return base64.b64encode(png_bytes).decode('utf-8')
        except Exception as e:
            print(f"Error getting QR: {e}")
        return None

    async def wait_for_login(self):
        """Waits until login is detected."""
        if not self.page:
            return
            
        try:
            print("Waiting for login (pane-side)...")
            
            # Check if we were logged out (QR code visible)
            try:
                qr_code = self.page.locator('canvas[aria-label="Scan this QR code"]')
                if await qr_code.count() > 0:
                    print("⚠️ Session expired or invalid. Please scan QR code again.")
            except:
                pass

            await self.page.wait_for_selector("#pane-side", timeout=0) 
            print("Login detected! (Persistent session active)")
            # No need to manual save with persistent context
        except Exception as e:
            print(f"Error waiting for login: {e}")

    async def send_message(self, phone, message, image_path=None):
        if not self.page:
            return False
        
        try:
            # Navigate to the chat
            url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
            print(f"Navigating to {url}")
            await self.page.goto(url)
            
            # Wait for the main chat frame to load
            print("Waiting for chat to load...")
            message_box = self.page.locator('div[contenteditable="true"][data-tab="10"]')
            await message_box.wait_for(state="visible", timeout=45000)
            print("Chat loaded.")

            if image_path:
                print(f"Attaching image: {image_path}")
                attach_btn = self.page.locator('span[data-icon="plus"]')
                await attach_btn.click()
                
                # Check for input
                file_input = self.page.locator('input[type="file"]').first
                await file_input.set_input_files(image_path)
                
                send_btn = self.page.locator('span[data-icon="send"]')
                await send_btn.wait_for(state="visible", timeout=15000)
                
                await send_btn.click()
                print("Image sent.")
                await asyncio.sleep(3) # Wait for upload
                self.log_message(phone, message if message else "Image Attachment", "success")
                return True

            # Text only flow
            print("Sending text message...")
            await message_box.click() 
            await asyncio.sleep(0.5)
            await message_box.press("Enter")
            
            await asyncio.sleep(2)
            # No need to manual save
            
            self.log_message(phone, message, "success")
            return True
        except Exception as e:
            print(f"Error sending msg: {e}")
            self.log_message(phone, message, f"error: {str(e)}")
            return False

    def log_message(self, phone, message, status):
        try:
            import csv
            import os
            from datetime import datetime
            
            # 1. Try default location (Exe folder)
            csv_path = os.path.join(config.EXEC_DIR, "conversations.csv")
            
            # 2. If blocked or read-only, try AppData
            if not os.access(config.EXEC_DIR, os.W_OK):
                appdata = os.getenv('APPDATA')
                if appdata:
                    csv_path = os.path.join(appdata, "ControlWHA", "conversations.csv")
                    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # Try writing
                file_exists = os.path.exists(csv_path)
                with open(csv_path, mode='a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["Timestamp", "Phone", "Message", "Status"])
                    writer.writerow([timestamp, phone, message, status])
                print(f"Logged to CSV: {csv_path}")
            
            except PermissionError:
                print(f"⚠️ CSV Locked or Permission Denied: {csv_path}. Trying backup file...")
                # 3. Fallback: Create a unique backup file if main is locked (e.g. open in Excel)
                backup_name = f"conversations_{datetime.now().strftime('%Y%m%d')}.csv"
                backup_path = os.path.join(os.path.dirname(csv_path), backup_name)
                
                with open(backup_path, mode='a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, phone, message, status])
                print(f"✅ Logged to BACKUP CSV: {backup_path}")

        except Exception as e:
            print(f"❌ Error logging to CSV (All attempts failed): {e}")
            
    async def get_messages(self, phone):
        pass

    async def on_context_closed(self):
        print("⚠️ Browser Context Closed!")
        self.page = None
        self.context = None
        
        if self.on_browser_close_callback:
            print("Triggering on_browser_close_callback...")
            await self.on_browser_close_callback()

    async def close(self):
        print("Closing Playwright Service...")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        
        self.page = None
        self.context = None
        self.playwright = None

service = WhatsAppService()
