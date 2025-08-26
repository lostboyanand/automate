from playwright.sync_api import sync_playwright
import time
import logging

def run_uber_signup(email, otp_code):  # Removed default values
    """
    Run Uber signup automation with dynamic email and OTP
    
    Args:
        email (str): Email address from Telegram user
        otp_code (str): OTP code from Telegram user
    
    Returns:
        dict: Status and message
    """
    
    print(f"🚀 Starting automation for email: {email}")
    print(f"🔐 Using OTP: {otp_code}")
    
    with sync_playwright() as p:
        # Launch browser - headless for server, visible for local testing
        browser = p.chromium.launch(
            headless=True,  # Change to False for local testing
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        # Create a browser context with popups allowed
        context = browser.new_context(
            accept_downloads=True,
            has_touch=False,
            ignore_https_errors=False,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        
        # Enable JavaScript popup dialogs (alert, confirm, prompt)
        context.set_default_timeout(30000)  # 30 seconds timeout
        page = context.new_page()
        
        # Handle popups/new windows
        page.on("popup", lambda popup: print(f"Popup opened: {popup.url}"))
        
        # Handle dialog events (alert, confirm, prompt)
        context.on("dialog", lambda dialog: dialog.accept())
        
        try:
            # Navigate to Uber homepage
            page.goto('https://www.uber.com/in/en/', wait_until='networkidle')
            
            # Click sign up button
            signup_button = page.get_by_role('button', name='Sign up to ride, drive, and')
            print("Found signup button, clicking it...")
            signup_button.click()
            
            # Wait for potential popup
            time.sleep(3)
            print("After clicking signup button")
            
            # Check for popup/new window
            pages = context.pages
            print(f"Number of pages/windows open: {len(pages)}")
            
            # If more than one page is open, the second one is likely the popup
            if len(pages) > 1:
                popup_page = pages[1]  # Use the popup page
                print(f"Found popup with URL: {popup_page.url}")
                
                # Look for Ride undefined link in the popup
                try:
                    popup_page.get_by_role('link', name='Ride undefined').click()
                    time.sleep(1)
                    print("Clicked 'Ride undefined' in popup")
                except Exception as e:
                    print(f"Error clicking 'Ride undefined': {e}")
                    print("Continuing without manual intervention...")
                
                # Continue using the popup page
                page = popup_page  # Switch to using the popup page for the rest of the script
            else:
                # No popup detected, try to find the Ride option on the current page
                try:
                    ride_link = page.get_by_text("Ride")
                    if ride_link.count() > 0:
                        print("Found Ride link on current page")
                        ride_link.first.click()
                        time.sleep(1)
                except Exception as e:
                    print(f"Could not find Ride option: {e}")
                    print("Continuing...")
            
            # Continue with Sign up
            print("Looking for Sign up link...")
            try:
                page.get_by_role('link', name='Sign up').click()
                print("Clicked Sign up link")
            except Exception as e:
                print(f"Error clicking Sign up link: {e}")
                print("Continuing...")
            
            time.sleep(1)
            
            # Click forward button
            try:
                page.get_by_test_id('forward-button').click()
                print("Clicked forward button")
            except Exception as e:
                print(f"Error clicking forward button: {e}")
                print("Continuing...")
            
            # Enter email (FROM TELEGRAM BOT)
            try:
                email_field = page.get_by_role('textbox', name='Enter phone number or email')
                email_field.click()
                email_field.fill(email)  # Using dynamic email from bot
                print(f"✅ Entered email: {email}")
                page.get_by_test_id('forward-button').click()
                print("Clicked forward button after email")
            except Exception as e:
                print(f"Error with email entry: {e}")
                return {"status": "error", "message": f"Email entry failed: {str(e)}"}
            
            # Handle CAPTCHA
            print("\n==== CAPTCHA DETECTION ====")
            print("Checking for CAPTCHA verification...")
            
            time.sleep(5)
            
            try:
                captcha_frame = page.locator('iframe[title="Verification challenge"]')
                if captcha_frame.count() > 0:
                    print("⚠️ CAPTCHA detected")
                    return {"status": "captcha_required", "message": "CAPTCHA verification required"}
                else:
                    print("✅ No CAPTCHA detected, continuing...")
            except Exception as e:
                print(f"CAPTCHA detection error: {e}")
            
            # Handle OTP verification (FROM TELEGRAM BOT)
            print("\n==== OTP VERIFICATION ====")
            print("Waiting for OTP field...")
            
            try:
                # Wait for OTP fields to appear
                page.wait_for_selector('#EMAIL_OTP_CODE-0', timeout=30000)
                
                # Split the OTP code into individual digits
                otp_digits = list(otp_code)  # Using dynamic OTP from bot
                
                print(f"✅ Entering OTP: {otp_code}")
                # Fill in OTP digits
                for i in range(min(4, len(otp_digits))):
                    page.locator(f'#EMAIL_OTP_CODE-{i}').fill(otp_digits[i])
                    time.sleep(0.5)
                
                print("🎉 OTP entered successfully!")
                
                # Wait for final submission
                time.sleep(3)
                
                # Check for success
                try:
                    if "welcome" in page.url.lower() or "dashboard" in page.url.lower():
                        return {"status": "success", "message": "Account created successfully!"}
                    else:
                        return {"status": "completed", "message": "Process completed - verify manually"}
                except:
                    return {"status": "completed", "message": "OTP submitted successfully"}
                    
            except Exception as e:
                print(f"OTP verification error: {e}")
                return {"status": "error", "message": f"OTP error: {str(e)}"}
            
        except Exception as e:
            print(f"Overall Error: {e}")
            return {"status": "error", "message": str(e)}
        
        finally:
            browser.close()

# For testing locally with custom values
if __name__ == "__main__":
    test_email = input("Enter test email: ")
    test_otp = input("Enter test OTP: ")
    result = run_uber_signup(email=test_email, otp_code=test_otp)
    print(f"Result: {result}")