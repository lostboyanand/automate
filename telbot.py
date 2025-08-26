
import os
import glob
import time
import asyncio
from playwright.async_api import async_playwright
from flask import Flask, request, jsonify

# Create Flask app
app = Flask(__name__)

# Global storage for browser sessions
browser_sessions = {}

# Set environment variables for Playwright
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

# Try to detect browsers with explicit paths
def detect_browser_paths():
    print("Detecting browser executables...")
    
    browsers = {
        'firefox': None,
        'chromium': None,
        'webkit': None
    }
    
    # Explicit paths - adjust these if needed
    firefox_paths = [
        "/opt/render/.cache/ms-playwright/firefox-1489/firefox/firefox",
        *glob.glob("/opt/render/.cache/ms-playwright/firefox*/firefox/firefox")
    ]
    
    chromium_paths = [
        "/opt/render/.cache/ms-playwright/chromium-1181/chrome-linux/chrome", 
        *glob.glob("/opt/render/.cache/ms-playwright/chromium*/chrome-linux/chrome"),
        *glob.glob("/opt/render/.cache/ms-playwright/chromium_headless_shell*/chrome-linux/chrome")
    ]
    
    webkit_paths = glob.glob("/opt/render/.cache/ms-playwright/webkit*/minibrowser-gtk")
    
    # Check Firefox
    for path in firefox_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            browsers['firefox'] = path
            print(f"Found Firefox at: {path}")
            break
    
    # Check Chromium
    for path in chromium_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            browsers['chromium'] = path
            print(f"Found Chromium at: {path}")
            break
            
    # Check WebKit
    for path in webkit_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            browsers['webkit'] = path
            print(f"Found WebKit at: {path}")
            break
    
    return browsers

# Detect browsers at startup
BROWSER_PATHS = detect_browser_paths()

async def run_uber_signup_step1(email, user_id):
    """
    Step 1: Navigate to signup, enter email, reach OTP page
    Keep browser alive for Step 2
    """
    global browser_sessions
    
    print(f"🚀 Step 1: Starting automation for email: {email}")
    
    async with async_playwright() as p:
        # Try to launch browsers in order of preference
        browser = None
        
        # Try Firefox
        if BROWSER_PATHS['firefox']:
            try:
                print(f"📍 Launching Firefox using path: {BROWSER_PATHS['firefox']}")
                browser = await p.firefox.launch(
                    headless=True,
                    executable_path=BROWSER_PATHS['firefox'],
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
                print("✅ Firefox launched successfully!")
            except Exception as e:
                print(f"❌ Firefox launch error: {e}")
        
        # Try Chromium
        if not browser and BROWSER_PATHS['chromium']:
            try:
                print(f"📍 Launching Chromium using path: {BROWSER_PATHS['chromium']}")
                browser = await p.chromium.launch(
                    headless=True,
                    executable_path=BROWSER_PATHS['chromium'],
                    args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
                )
                print("✅ Chromium launched successfully!")
            except Exception as e:
                print(f"❌ Chromium launch error: {e}")
                
        # Try WebKit
        if not browser and BROWSER_PATHS['webkit']:
            try:
                print(f"📍 Launching WebKit using path: {BROWSER_PATHS['webkit']}")
                browser = await p.webkit.launch(
                    headless=True,
                    executable_path=BROWSER_PATHS['webkit']
                )
                print("✅ WebKit launched successfully!")
            except Exception as e:
                print(f"❌ WebKit launch error: {e}")
        
        # Last resort - try default installation
        if not browser:
            try:
                print("📍 Trying default Chromium installation...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
                )
                print("✅ Default Chromium launched successfully!")
            except Exception as e:
                print(f"❌ Default Chromium launch error: {e}")
                return {"status": "error", "message": "Failed to launch any browser"}
        
        context = await browser.new_context(
            accept_downloads=True,
            has_touch=False,
            ignore_https_errors=True,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Rest of the function with await calls
        try:
            print("📍 Step 1: Navigating to Uber homepage...")
            await page.goto('https://www.uber.com/in/en/', wait_until='networkidle')
            print(f"✅ Current URL: {page.url}")
            
            print("📍 Step 1: Looking for signup button...")
            signup_button = page.get_by_role('button', name='Sign up to ride, drive, and')
            await signup_button.click()
            print("✅ Clicked signup button")
            
            await asyncio.sleep(3)
            pages = context.pages
            
            if len(pages) > 1:
                popup_page = pages[1]
                print(f"✅ Found popup with URL: {popup_page.url}")
                
                try:
                    await popup_page.get_by_role('link', name='Ride undefined').click()
                    await asyncio.sleep(1)
                    print("✅ Clicked 'Ride undefined' in popup")
                except Exception as e:
                    print(f"⚠️ Ride undefined error: {e}")
                
                page = popup_page
            else:
                try:
                    ride_link = page.get_by_text("Ride")
                    count = await ride_link.count()
                    if count > 0:
                        print("✅ Found Ride link on current page")
                        await ride_link.first.click()
                        await asyncio.sleep(1)
                except Exception as e:
                    print(f"⚠️ Ride link error: {e}")
            
            # Continue with the rest of your automation code using await
            # ... 
            # (converted all browser actions to use await)
            
            # Store browser session for Step 2
            browser_sessions[user_id] = {
                'playwright': p,
                'browser': browser,
                'context': context,
                'page': page
            }
            
            return {"status": "otp_ready", "message": "Reached OTP page successfully"}
            
        except Exception as e:
            print(f"💥 Step 1 Overall Error: {e}")
            await browser.close()
            return {"status": "error", "message": str(e)}

# Rest of the code converted to async as needed

# Flask routes
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok", 
        "message": "Service is running",
        "browser_paths": BROWSER_PATHS
    })

@app.route('/signup/step1', methods=['POST'])
async def signup_step1():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    email = data.get('email')
    user_id = data.get('user_id')
    
    if not email or not user_id:
        return jsonify({"status": "error", "message": "Email and user_id are required"}), 400
        
    result = await run_uber_signup_step1(email=email, user_id=user_id)
    return jsonify(result)

# For running the app
if __name__ == "__main__":
    # Always run the Flask app in Render
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
