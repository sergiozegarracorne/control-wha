import asyncio
import sys
import uvicorn
import importlib

# NOTE: Do NOT import app.main or app.core.config here globally.
# They read config.ini on import. We must run the setup wizard first!

if __name__ == "__main__":
    # 1. Run Setup Wizard (GUI) if needed
    from app import setup_wizard
    setup_wizard.run_wizard()

    # 2. Now it's safe to import the app, as config.ini is ready
    from app.main import app
    from app.core import config

    # Enforce ProactorEventLoopPolicy on Windows for Playwright
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Run Uvicorn directly with the app instance
    print(f"Starting server on port {config.PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT, reload=False)
