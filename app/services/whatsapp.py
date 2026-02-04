import asyncio
import base64
import os
from playwright.async_api import async_playwright, Page, BrowserContext
from app.core import config

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

    async def start(self):
        if self.page:
            return

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
        except Exception as e:
            print(f"Error launching persistent context: {e}")
            # Fallback if channel fails or locked?
            raise e

        # Get the first page or create new
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()
        
        try:
            print(f"Navigating to {config.WHATSAPP_URL}")
            await self.page.goto(config.WHATSAPP_URL, timeout=60000)
        except Exception as e:
            print(f"Error navigating: {e}")

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
            from datetime import datetime
            
            csv_file = os.path.join(config.EXEC_DIR, "conversations.csv")
            file_exists = os.path.exists(csv_file)
            
            with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Timestamp", "Phone", "Message", "Status"])
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([timestamp, phone, message, status])
                print(f"Logged to CSV: {phone}")
        except Exception as e:
            print(f"Error logging to CSV: {e}")
            
    async def get_messages(self, phone):
        pass

    async def close(self):
        print("Closing persistent context...")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()

service = WhatsAppService()
