import os
import time
import logging
from playwright.sync_api import sync_playwright

# Global storage for browser sessions
browser_sessions = {}

def run_uber_signup_step1(email, user_id):
    """
    Step 1: Navigate to signup, enter email, reach OTP page
    Keep browser alive for Step 2
    """
    global browser_sessions
    
    print(f"🚀 Step 1: Starting automation for email: {email}")
    
    # Set environment variable for Playwright
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    
    p = sync_playwright().start()
    
    # Use Chrome with exact path on Render
    print("📍 Launching Chrome browser...")
    browser = p.chromium.launch(
        headless=True,
        executable_path="/opt/render/.cache/ms-playwright/chromium-1181/chrome-linux/chrome",
        args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
    )
    
    context = browser.new_context(
        accept_downloads=True,
        has_touch=False,
        ignore_https_errors=False,
        viewport={'width': 1280, 'height': 800},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    )
    
    context.set_default_timeout(30000)
    page = context.new_page()
    
    # Handle popups/new windows
    page.on("popup", lambda popup: print(f"Popup opened: {popup.url}"))
    context.on("dialog", lambda dialog: dialog.accept())
    
    try:
        print("📍 Step 1: Navigating to Uber homepage...")
        page.goto('https://www.uber.com/in/en/', wait_until='networkidle')
        print(f"✅ Current URL: {page.url}")
        
        print("📍 Step 1: Looking for signup button...")
        signup_button = page.get_by_role('button', name='Sign up to ride, drive, and')
        print("✅ Found signup button, clicking it...")
        signup_button.click()
        
        time.sleep(3)
        print("📍 Step 1: Checking for popups...")
        pages = context.pages
        print(f"✅ Number of pages/windows open: {len(pages)}")
        
        if len(pages) > 1:
            popup_page = pages[1]
            print(f"✅ Found popup with URL: {popup_page.url}")
            
            try:
                popup_page.get_by_role('link', name='Ride undefined').click()
                time.sleep(1)
                print("✅ Clicked 'Ride undefined' in popup")
            except Exception as e:
                print(f"⚠️ Ride undefined error: {e}")
            
            page = popup_page
        else:
            try:
                ride_link = page.get_by_text("Ride")
                if ride_link.count() > 0:
                    print("✅ Found Ride link on current page")
                    ride_link.first.click()
                    time.sleep(1)
            except Exception as e:
                print(f"⚠️ Ride link error: {e}")
        
        print("📍 Step 1: Looking for Sign up link...")
        try:
            page.get_by_role('link', name='Sign up').click()
            print("✅ Clicked Sign up link")
        except Exception as e:
            print(f"⚠️ Sign up link error: {e}")
        
        time.sleep(1)
        
        print("📍 Step 1: Clicking forward button...")
        try:
            page.get_by_test_id('forward-button').click()
            print("✅ Clicked forward button")
        except Exception as e:
            print(f"⚠️ Forward button error: {e}")
        
        print("📍 Step 1: Entering email...")
        try:
            email_field = page.get_by_role('textbox', name='Enter phone number or email')
            email_field.click()
            email_field.fill(email)
            print(f"✅ Entered email: {email}")
            
            page.get_by_test_id('forward-button').click()
            print("✅ Clicked forward button after email")
        except Exception as e:
            print(f"❌ Email entry error: {e}")
            browser.close()
            p.stop()
            return {"status": "error", "message": f"Email entry failed: {str(e)}"}
        
        print("📍 Step 1: Checking for CAPTCHA...")
        time.sleep(5)
        
        try:
            captcha_frame = page.locator('iframe[title="Verification challenge"]')
            if captcha_frame.count() > 0:
                print("⚠️ CAPTCHA detected")
                browser.close()
                p.stop()
                return {"status": "captcha_required", "message": "CAPTCHA verification required"}
            else:
                print("✅ No CAPTCHA detected")
        except Exception as e:
            print(f"⚠️ CAPTCHA detection error: {e}")
        
        print("📍 Step 1: Waiting for OTP fields...")
        try:
            page.wait_for_selector('#EMAIL_OTP_CODE-0', timeout=30000)
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
            browser.close()
            p.stop()
            return {"status": "error", "message": "Could not reach OTP page"}
            
    except Exception as e:
        print(f"💥 Step 1 Overall Error: {e}")
        browser.close()
        p.stop()
        return {"status": "error", "message": str(e)}

def run_uber_signup_step2(otp_code, user_id):
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
            page.locator(f'#EMAIL_OTP_CODE-{i}').fill(otp_digits[i])
            print(f"✅ Entered digit {i+1}: {otp_digits[i]}")
            time.sleep(0.5)
        
        print("📍 Step 2: Waiting for submission...")
        time.sleep(3)
        
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
            session['browser'].close()
            session['playwright'].stop()
            del browser_sessions[user_id]
            print("✅ Browser session cleaned up")
        except:
            pass

# For testing locally
if __name__ == "__main__":
    test_email = input("Enter test email: ")
    result1 = run_uber_signup_step1(email=test_email, user_id="test_user")
    print(f"Step 1 Result: {result1}")
    
    if result1["status"] == "otp_ready":
        test_otp = input("Enter real OTP: ")
        result2 = run_uber_signup_step2(otp_code=test_otp, user_id="test_user")
        print(f"Step 2 Result: {result2}")