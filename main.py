import os
import telebot
from create_account import run_uber_signup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Bot token from environment
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set!")

bot = telebot.TeleBot(TOKEN)
user_sessions = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, """
🤖 Learning Automation Bot

Commands:
/create - Start automation process
/status - Check bot status
    """)

@bot.message_handler(commands=['status'])
def status(message):
    bot.reply_to(message, "✅ Bot is running on Render!")

@bot.message_handler(commands=['create'])
def ask_email(message):
    bot.reply_to(message, "📧 Send me an email address:")
    bot.register_next_step_handler(message, get_email)

def get_email(message):
    email = message.text.strip()
    
    # Basic validation
    if '@' not in email:
        bot.reply_to(message, "❌ Invalid email! Try again:")
        bot.register_next_step_handler(message, get_email)
        return
    
    user_sessions[message.chat.id] = {'email': email}
    bot.reply_to(message, f"✅ Email saved: {email}\n\n🔐 Now send OTP code (4 digits):")
    bot.register_next_step_handler(message, get_otp)

def get_otp(message):
    otp = message.text.strip()
    
    if len(otp) != 4 or not otp.isdigit():
        bot.reply_to(message, "❌ OTP should be 4 digits! Try again:")
        bot.register_next_step_handler(message, get_otp)
        return
    
    email = user_sessions[message.chat.id]['email']
    
    bot.reply_to(message, f"🚀 Starting automation...\n📧 {email}\n🔐 {otp}")
    
    try:
        # Run automation in background
        result = run_uber_signup(email=email, otp_code=otp)
        
        if result['status'] == 'success':
            bot.send_message(message.chat.id, "✅ Process completed successfully!")
        else:
            bot.send_message(message.chat.id, f"⚠️ Issue: {result['message']}")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
    
    # Clear session
    if message.chat.id in user_sessions:
        del user_sessions[message.chat.id]

if __name__ == "__main__":
    print("🤖 Bot starting...")
    try:
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Error: {e}")


