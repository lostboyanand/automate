
import os
import glob
import time
import asyncio
import telebot
from telebot.async_telebot import AsyncTeleBot
from playwright.async_api import async_playwright
from flask import Flask, request, jsonify
import threading

# Create Flask app
app = Flask(__name__)

# Set up Telegram bot (replace with your actual token)
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
bot = AsyncTeleBot(BOT_TOKEN)

# Global storage for browser sessions and user states
browser_sessions = {}
user_states = {}  # Track what step each user is on

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
    
    p = await async_playwright().start()
    
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
            await p.stop()
            return {"status": "error", "message": "Failed to launch any browser"}
    
    context = await browser.new_context(
        accept_downloads=True,
        has_touch=False,
        ignore_https_errors=True,
        viewport={'width': 1280, 'height': 800},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )
    
    context.set_default_timeout(30000)
    page = await context.new_page()
    
    try:
        print("📍 Step 1: Navigating to Uber homepage...")
        await page.goto('https://www.uber.com/in/en/', wait_until='networkidle')
        print(f"✅ Current URL: {page.url}")
        
        print("📍 Step 1: Looking for signup button...")
        signup_button = page.get_by_role('button', name='Sign up to ride, drive, and')
        print("✅ Found signup button, clicking it...")
        await signup_button.click()
        
        await asyncio.sleep(3)
        print("📍 Step 1: Checking for popups...")
        pages = context.pages
        print(f"✅ Number of pages/windows open: {len(pages)}")
        
        if len(pages) > 1:
            popup_page = pages[1]
            print(f"✅ Found popup with URL: {await popup_page.url}")
            
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
        
        print("📍 Step 1: Looking for Sign up link...")
        try:
            await page.get_by_role('link', name='Sign up').click()
            print("✅ Clicked Sign up link")
        except Exception as e:
            print(f"⚠️ Sign up link error: {e}")
        
        await asyncio.sleep(1)
        
        print("📍 Step 1: Clicking forward button...")
        try:
            await page.get_by_test_id('forward-button').click()
            print("✅ Clicked forward button")
        except Exception as e:
            print(f"⚠️ Forward button error: {e}")
        
        print("📍 Step 1: Entering email...")
        try:
            email_field = page.get_by_role('textbox', name='Enter phone number or email')
            await email_field.click()
            await email_field.fill(email)
            print(f"✅ Entered email: {email}")
            
            await page.get_by_test_id('forward-button').click()
            print("✅ Clicked forward button after email")
        except Exception as e:
            print(f"❌ Email entry error: {e}")
            await browser.close()
            await p.stop()
            return {"status": "error", "message": f"Email entry failed: {str(e)}"}
        
        print("📍 Step 1: Checking for CAPTCHA...")
        await asyncio.sleep(5)
        
        try:
            captcha_frame = page.locator('iframe[title="Verification challenge"]')
            count = await captcha_frame.count()
            if count > 0:
                print("⚠️ CAPTCHA detected")
                await browser.close()
                await p.stop()
                return {"status": "captcha_required", "message": "CAPTCHA verification required"}
            else:
                print("✅ No CAPTCHA detected")
        except Exception as e:
            print(f"⚠️ CAPTCHA detection error: {e}")
        
        print("📍 Step 1: Waiting for OTP fields...")
        try:
            await page.wait_for_selector('#EMAIL_OTP_CODE-0', timeout=30000)
            print("🎉 OTP fields appeared! Ready for real OTP...")
            
            # Store browser session for Step 2
            browser_sessions[user_id] = {
                'playwright': p,
                'browser': browser,
                'context': context,
                'page': page
            }
            
            return {"status": "otp_ready", "message": "Reached OTP page successfully"}
            
        except Exception as e:
            print(f"❌ OTP fields not found: {e}")
            await browser.close()
            await p.stop()
            return {"status": "error", "message": "Could not reach OTP page"}
            
    except Exception as e:
        print(f"💥 Step 1 Overall Error: {e}")
        await browser.close()
        await p.stop()
        return {"status": "error", "message": str(e)}

async def run_uber_signup_step2(otp_code, user_id):
    """
    Step 2: Enter real OTP and complete signup
    Use existing browser session from Step 1
    """
    global browser_sessions
    
    print(f"🚀 Step 2: Starting with real OTP: {otp_code}")
    
    if user_id not in browser_sessions:
        return {"status": "error", "message": "No active browser session found"}
    
    session = browser_sessions[user_id]
    page = session['page']
    
    try:
        print("📍 Step 2: Entering real OTP digits...")
        
        otp_digits = list(otp_code)
        for i in range(min(4, len(otp_digits))):
            await page.locator(f'#EMAIL_OTP_CODE-{i}').fill(otp_digits[i])
            print(f"✅ Entered digit {i+1}: {otp_digits[i]}")
            await asyncio.sleep(0.5)
        
        print("📍 Step 2: Waiting for submission...")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"📍 Current URL after OTP: {current_url}")
        
        if "welcome" in current_url.lower() or "dashboard" in current_url.lower():
            print("🎉 SUCCESS: Account creation completed!")
            return {"status": "success", "message": "Account created successfully!"}
        else:
            print("✅ OTP submitted, process completed")
            return {"status": "completed", "message": "OTP submitted successfully"}
            
    except Exception as e:
        print(f"❌ Step 2 Error: {e}")
        return {"status": "error", "message": f"OTP entry failed: {str(e)}"}
        
    finally:
        print("🔄 Cleaning up browser session...")
        try:
            await session['browser'].close()
            await session['playwright'].stop()
            del browser_sessions[user_id]
            print("✅ Browser session cleaned up")
        except:
            pass

# Telegram bot handlers
@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
    await bot.reply_to(message, "Welcome to the Uber Signup Bot! Send /signup to begin.")

@bot.message_handler(commands=['signup'])
async def start_signup(message):
    user_id = str(message.from_user.id)
    
    # Clear any existing state
    if user_id in user_states:
        del user_states[user_id]
    
    # Set initial state
    user_states[user_id] = {'state': 'awaiting_email'}
    
    await bot.reply_to(message, "Please send me the email you want to use for signing up with Uber.")

@bot.message_handler(func=lambda message: str(message.from_user.id) in user_states and user_states[str(message.from_user.id)]['state'] == 'awaiting_email')
async def process_email(message):
    user_id = str(message.from_user.id)
    email = message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        await bot.reply_to(message, "That doesn't look like a valid email. Please send a valid email address.")
        return
    
    await bot.reply_to(message, f"Starting signup process with email: {email}. Please wait while I navigate to the OTP page...")
    
    # Run the browser automation
    result = await run_uber_signup_step1(email=email, user_id=user_id)
    
    if result["status"] == "otp_ready":
        # Update user state
        user_states[user_id] = {'state': 'awaiting_otp', 'email': email}
        await bot.send_message(message.chat.id, "Great! I've reached the OTP page. Please check your email and send me the OTP code you received.")
    elif result["status"] == "captcha_required":
        await bot.send_message(message.chat.id, "Sorry, a CAPTCHA was detected. Please try again later or with a different email.")
    else:
        await bot.send_message(message.chat.id, f"Error: {result['message']}. Please try again with /signup.")

@bot.message_handler(func=lambda message: str(message.from_user.id) in user_states and user_states[str(message.from_user.id)]['state'] == 'awaiting_otp')
async def process_otp(message):
    user_id = str(message.from_user.id)
    otp = message.text.strip()
    
    # Basic OTP validation
    if not otp.isdigit() or len(otp) < 4:
        await bot.reply_to(message, "That doesn't look like a valid OTP. Please send the numeric code you received.")
        return
    
    await bot.reply_to(message, f"Processing OTP: {otp}. Please wait...")
    
    # Complete signup with OTP
    result = await run_uber_signup_step2(otp_code=otp, user_id=user_id)
    
    if result["status"] == "success" or result["status"] == "completed":
        await bot.send_message(message.chat.id, "🎉 Success! Your Uber account has been created successfully!")
        # Clear user state
        del user_states[user_id]
    else:
        await bot.send_message(message.chat.id, f"Error: {result['message']}. Please try again later.")

# Flask routes for API and webhook
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

@app.route('/signup/step2', methods=['POST'])
async def signup_step2():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400
    
    otp = data.get('otp')
    user_id = data.get('user_id')
    
    if not otp or not user_id:
        return jsonify({"status": "error", "message": "OTP and user_id are required"}), 400
        
    result = await run_uber_signup_step2(otp_code=otp, user_id=user_id)
    return jsonify(result)

# Telegram webhook endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        await bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

# Set up Telegram webhook
def setup_webhook():
    if BOT_TOKEN:
        webhook_url = f"https://automate-40s6.onrender.com/{BOT_TOKEN}"
        bot.remove_webhook()
        time.sleep(0.5)
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set to {webhook_url}")
    else:
        print("WARNING: No Telegram bot token provided. Telegram bot functionality is disabled.")

# Start the bot in a separate thread
def start_bot_polling():
    if BOT_TOKEN:
        print("Starting Telegram bot polling...")
        asyncio.run(bot.polling())
    else:
        print("WARNING: No Telegram bot token provided. Telegram bot polling is disabled.")

# For running the app
if __name__ == "__main__":
    # Set up webhook for production or polling for development
    if os.environ.get('RENDER') == 'true':
        setup_webhook()
    else:
        # Start polling in a separate thread for local testing
        threading.Thread(target=start_bot_polling).start()
    
    # Start Flask server
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
