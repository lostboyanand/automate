import os
import requests
from requests.sessions import Session
import ssl
import telebot
import threading
import flask
from flask import Flask, request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from create_account import run_uber_signup_step1, run_uber_signup_step2

# Monkey-patch Session to always disable SSL verification
old_request = Session.request

def new_request(self, *args, **kwargs):
    kwargs['verify'] = False
    return old_request(self, *args, **kwargs)

Session.request = new_request

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Create bot instance and Flask app
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Store user sessions
user_sessions = {}

def start_health_server():
    """Start a simple HTTP server for Render's health checks"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"🌐 Health server starting on port {port}")
    server.serve_forever()

# Define command handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = """
🚗 Welcome to Uber Signup Bot!

Commands:
/create - Start creating an Uber account (Two-step process)
/status - Check bot status
/help - Show this message

✨ New Flow:
1. Send email → I'll start automation
2. I'll reach OTP page → You send real OTP
3. I'll complete the signup!

Ready to automate your learning! 🚀
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['status'])
def bot_status(message):
    bot.reply_to(message, "✅ Bot is running on Render and ready!")

@bot.message_handler(commands=['create'])
def start_signup(message):
    bot.reply_to(message, """
📧 Please send me the email address you want to use for the Uber account:

🔄 **New Smart Flow:**
1. I'll start automation with your email
2. I'll stop at OTP page and ask for real OTP
3. You check your email and send me the real code
4. I'll complete the signup!

Much better than asking for OTP before it exists! 🎯
    """)
    bot.register_next_step_handler(message, process_email)

def process_email(message):
    email = message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        bot.reply_to(message, "❌ That doesn't look like a valid email. Please try again:")
        bot.register_next_step_handler(message, process_email)
        return
    
    # Store email in user session
    user_sessions[message.chat.id] = {
        'email': email,
        'step': 'processing_email'
    }
    
    bot.reply_to(message, f"""
✅ Email: {email}

🚀 Starting automation...
📧 I'll navigate to Uber, enter your email, and reach the OTP page
⏳ Then I'll pause and ask for the real OTP from your inbox!

Please wait...
    """)
    
    try:
        # Run STEP 1: Navigate and enter email until OTP page
        result = run_uber_signup_step1(email=email, user_id=message.chat.id)
        
        if result["status"] == "otp_ready":
            user_sessions[message.chat.id]['step'] = 'waiting_for_otp'
            
            bot.send_message(message.chat.id, f"""
🎉 Perfect! I've successfully:
✅ Navigated to Uber signup
✅ Entered your email: {email}
✅ Reached the OTP verification page

📱 **Now check your email inbox!**
🔐 **Send me the 4-digit OTP code when you receive it**

The browser is waiting and ready for your real OTP...
            """)
            bot.register_next_step_handler(message, process_real_otp)
            
        elif result["status"] == "captcha_required":
            bot.send_message(message.chat.id, """
🤖 CAPTCHA Challenge Detected!

This is completely normal when learning automation. 
CAPTCHAs are designed to stop bots, so this means the site is working as expected.

For learning purposes, this shows you:
✅ How automation works up to security measures
✅ Where human intervention is needed
✅ Real-world challenges in automation

Try again with /create - sometimes CAPTCHAs don't appear!
            """)
            
        elif result["status"] == "error":
            bot.send_message(message.chat.id, f"""
❌ Issue during email entry phase:

🔧 Error: {result['message']}

This could be due to:
• Site changes
• Network issues  
• Timing problems

Try again with /create or check the logs!
            """)
            
        else:
            bot.send_message(message.chat.id, f"📊 Unexpected result: {result}")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"""
💥 Unexpected error during automation:

{str(e)}

Please try again with /create
        """)
        print(f"Bot error in process_email: {e}")
    
    finally:
        # Don't clear session yet - we need it for OTP step
        pass

def process_real_otp(message):
    otp = message.text.strip()
    
    # Basic OTP validation
    if len(otp) != 4 or not otp.isdigit():
        bot.reply_to(message, """
❌ OTP should be exactly 4 digits. 

Please check your email and send the correct 4-digit code:
        """)
        bot.register_next_step_handler(message, process_real_otp)
        return
    
    # Check if session exists
    if message.chat.id not in user_sessions:
        bot.reply_to(message, """
❌ Session expired or not found. 

Please start over with /create
        """)
        return
    
    email = user_sessions[message.chat.id]['email']
    
    bot.reply_to(message, f"""
🔐 Received OTP: {otp}
📧 For email: {email}

🚀 Continuing automation...
⏳ Entering your real OTP and completing the signup process...
    """)
    
    try:
        # Run STEP 2: Enter real OTP and complete
        result = run_uber_signup_step2(otp_code=otp, user_id=message.chat.id)
        
        if result["status"] == "success":
            bot.send_message(message.chat.id, f"""
🎉 AMAZING! Account Creation Successful!

✅ {result['message']}

Your Uber account should now be ready to use!
🚗 You can download the Uber app and log in with:
📧 Email: {email}

Great job learning automation! 🚀
            """)
            
        elif result["status"] == "completed":
            bot.send_message(message.chat.id, f"""
✅ Process Completed!

📋 {result['message']}

The OTP was entered successfully. Check your email or the Uber app to confirm account status.

Good work! 🎯
            """)
            
        elif result["status"] == "error":
            bot.send_message(message.chat.id, f"""
❌ Issue during OTP entry:

🔧 {result['message']}

This could be due to:
• OTP expired or incorrect
• Session timeout
• Network issues

You may need to start over with /create
            """)
            
        else:
            bot.send_message(message.chat.id, f"📊 Result: {result}")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"""
💥 Error during OTP processing:

{str(e)}

The browser session may have been lost. Please try /create again.
        """)
        print(f"Bot error in process_real_otp: {e}")
    
    finally:
        # Clear user session
        if message.chat.id in user_sessions:
            del user_sessions[message.chat.id]
        
        bot.send_message(message.chat.id, """
Want to try creating another account? Use /create

Thanks for learning automation! 🤖✨
        """)

# Handle any other messages
@bot.message_handler(func=lambda message: True)
def handle_other(message):
    bot.reply_to(message, """
🤔 I didn't understand that command.

Available commands:
/start - Welcome message
/create - Start Uber account creation
/status - Check bot status
/help - Show help

Use /create to begin the automation process!
    """)

# Flask webhook routes
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
    webhook_url = f"{render_url}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook set to {webhook_url}", 200

# Start the server
if __name__ == "__main__":
    print("🤖 Bot is starting in webhook mode...")
    
    # Set webhook on startup
    render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
    webhook_url = f"{render_url}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook set to: {webhook_url}")
    
    # Start Flask server
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)