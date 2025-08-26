import os
import requests
from requests.sessions import Session
import ssl
import telebot
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from create_account import run_uber_signup  # Import your automation

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

# Create bot instance
bot = telebot.TeleBot(TOKEN)

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
/create - Start creating an Uber account
/status - Check bot status
/help - Show this message

Ready to automate your learning! 🚀
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['status'])
def bot_status(message):
    bot.reply_to(message, "✅ Bot is running on Render and ready!")

@bot.message_handler(commands=['create'])
def start_signup(message):
    bot.reply_to(message, "📧 Please send me the email address you want to use for the Uber account:")
    bot.register_next_step_handler(message, process_email)

def process_email(message):
    email = message.text.strip()
    
    # Basic email validation
    if '@' not in email or '.' not in email:
        bot.reply_to(message, "❌ That doesn't look like a valid email. Please try again with a valid email address:")
        bot.register_next_step_handler(message, process_email)
        return
    
    # Store email in user session
    user_sessions[message.chat.id] = {'email': email}
    
    bot.reply_to(message, f"✅ Email saved: {email}\n\n🔐 Now please send me the 4-digit OTP code:")
    bot.register_next_step_handler(message, process_otp)

def process_otp(message):
    otp = message.text.strip()
    
    # Basic OTP validation
    if len(otp) != 4 or not otp.isdigit():
        bot.reply_to(message, "❌ OTP should be exactly 4 digits. Please try again:")
        bot.register_next_step_handler(message, process_otp)
        return
    
    # Get email from session
    if message.chat.id not in user_sessions:
        bot.reply_to(message, "❌ Session expired. Please start over with /create")
        return
    
    email = user_sessions[message.chat.id]['email']
    
    # Show what we're about to do
    bot.reply_to(message, f"""
🚀 Starting Uber automation with:
📧 Email: {email}
🔐 OTP: {otp}

⏳ Please wait while I process this...
    """)
    
    try:
        # Run the automation with user's input
        result = run_uber_signup(email=email, otp_code=otp)
        
        # Handle different result types
        if result["status"] == "success":
            bot.send_message(message.chat.id, f"🎉 Success!\n\n✅ {result['message']}")
            
        elif result["status"] == "captcha_required":
            bot.send_message(message.chat.id, f"🤖 CAPTCHA detected!\n\n⚠️ {result['message']}\n\nThis is normal for learning automation!")
            
        elif result["status"] == "completed":
            bot.send_message(message.chat.id, f"✅ Process completed!\n\n📋 {result['message']}")
            
        elif result["status"] == "error":
            bot.send_message(message.chat.id, f"❌ Error occurred:\n\n🔧 {result['message']}\n\nTry again or check the logs!")
            
        else:
            bot.send_message(message.chat.id, f"📊 Result: {result}")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"💥 Unexpected error:\n\n{str(e)}\n\nPlease try again!")
        print(f"Bot error: {e}")  # For debugging
    
    finally:
        # Clear user session
        if message.chat.id in user_sessions:
            del user_sessions[message.chat.id]
        
        # Offer to try again
        bot.send_message(message.chat.id, "Want to try again? Use /create")

# Handle any other messages
@bot.message_handler(func=lambda message: True)
def handle_other(message):
    bot.reply_to(message, "🤔 I didn't understand that. Use /help to see available commands!")

# Start the bot
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    
    # Start health server for Render in background thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    print("✅ Health server started!")
    
    try:
        print("✅ Bot is running and ready!")
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"❌ Bot error: {e}")