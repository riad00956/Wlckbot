import logging
import sqlite3
import random
import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler, ChatMemberHandler
)
from telegram.constants import ParseMode

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8265396096:AAF-Fo0Tu8enZFXICc8_H7FRW3NUbFoZi2A"
OWNER_ID = 7832264582

# --- ফ্লাস্ক সেটআপ (রেন্ডার এর জন্য) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8000))
    web_app.run(host='0.0.0.0', port=port)

# --- ডেটাবেজ লজিক ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("welcome_msg", "আমাদের গ্রুপে আপনাকে স্বাগতম!")')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("leave_msg", "গ্রুপ থেকে বিদায় নিলেন। ভালো থাকবেন!")')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("photo_react_text", "খুব সুন্দর ছবি! 😍")')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("video_react_text", "দারুণ ভিডিও! 🔥")')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("emoji_list", "😐, 💔, 🙋, 🔥, ❤️")')
    cursor.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect('bot_database.db')
    res = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    conn.close()
    return res[0] if res else ""

def set_setting(key, value):
    conn = sqlite3.connect('bot_database.db')
    conn.execute('UPDATE settings SET value=? WHERE key=?', (value, key))
    conn.commit()
    conn.close()

def is_admin(user_id):
    conn = sqlite3.connect('bot_database.db')
    res = conn.execute('SELECT * FROM admins WHERE user_id=?', (user_id,)).fetchone()
    conn.close()
    return res is not None or user_id == OWNER_ID

# --- কিবোর্ড ---
def main_admin_kb():
    keyboard = [
        [InlineKeyboardButton("📝 Welcome Message", callback_data="set_welcome")],
        [InlineKeyboardButton("🏃 Leave Message", callback_data="set_leave")],
        [InlineKeyboardButton("🖼 Photo React Text", callback_data="set_photo_text")],
        [InlineKeyboardButton("🎥 Video React Text", callback_data="set_video_text")],
        [InlineKeyboardButton("🎭 Edit Emojis", callback_data="set_emojis")],
        [InlineKeyboardButton("🧳 Preview", callback_data="view_stats"), 
         InlineKeyboardButton("❌ Close", callback_data="close_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_main")]])

# --- হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("হ্যালো 😁, বট এখন চালু আছে। তোমার গ্রুপে এড করে নাও। 😸")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🛠 **Admin Control Panel**", 
                                   reply_markup=main_admin_kb(), 
                                   parse_mode=ParseMode.MARKDOWN)

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_main":
        await query.edit_message_text("🛠 **Admin Control Panel**", reply_markup=main_admin_kb())
    elif query.data == "set_welcome":
        context.user_data['waiting_for'] = "welcome_msg"
        await query.edit_message_text("📝 **নতুন ওয়েলকাম মেসেজটি লিখুন:**", reply_markup=back_kb())
    elif query.data == "set_leave":
        context.user_data['waiting_for'] = "leave_msg"
        await query.edit_message_text("🏃 **বিদায়ি মেসেজটি লিখুন:**", reply_markup=back_kb())
    elif query.data == "set_photo_text":
        context.user_data['waiting_for'] = "photo_react_text"
        await query.edit_message_text("🖼 **ছবির জন্য নতুন রিপ্লাই টেক্সট লিখুন:**", reply_markup=back_kb())
    elif query.data == "set_video_text":
        context.user_data['waiting_for'] = "video_react_text"
        await query.edit_message_text("🎥 **ভিডিওর জন্য নতুন রিপ্লাই টেক্সট লিখুন:**", reply_markup=back_kb())
    elif query.data == "set_emojis":
        context.user_data['waiting_for'] = "emoji_list"
        await query.edit_message_text("🎭 **ইমোজিগুলো কমা দিয়ে লিখুন:**\nউদাহরণ: `😐, 💔, 🙋`", reply_markup=back_kb())
    elif query.data == "view_stats":
        stats = (f"📊 **বর্তমান সেটিংস:**\n\n"
                 f"👋 Welcome: {get_setting('welcome_msg')}\n"
                 f"🏃 Leave: {get_setting('leave_msg')}\n"
                 f"🖼 Photo Text: {get_setting('photo_react_text')}\n"
                 f"🎥 Video Text: {get_setting('video_react_text')}\n"
                 f"🎭 Emojis: `{get_setting('emoji_list')}`")
        await query.edit_message_text(stats, reply_markup=back_kb())
    elif query.data == "close_panel":
        await query.message.delete()

async def input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('waiting_for')
    if target:
        set_setting(target, update.message.text)
        context.user_data['waiting_for'] = None
        await update.message.delete()
        await context.bot.send_message(update.effective_chat.id, "✅ সফলভাবে আপডেট হয়েছে!", reply_markup=main_admin_kb())

async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ফটো না ভিডিও তা চেক করে আলাদা মেসেজ দেয়া
    if update.message.photo:
        await update.message.reply_text(get_setting("photo_react_text"))
    elif update.message.video:
        await update.message.reply_text(get_setting("video_react_text"))
    
    # ছবির মতো ইমোজি রিঅ্যাকশন (র‍্যান্ডম)
    emoji_list = [e.strip() for e in get_setting("emoji_list").split(',')]
    random_emoji = random.choice(emoji_list)
    try:
        await update.message.set_reaction(reaction=[ReactionTypeEmoji(emoji=random_emoji)])
    except: pass

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    user = result.new_chat_member.user
    mention = user.mention_html()
    if result.old_chat_member.status in ["left", "kicked"] and result.new_chat_member.status == "member":
        await context.bot.send_message(update.effective_chat.id, f"{mention} {get_setting('welcome_msg')}", parse_mode=ParseMode.HTML)
    elif result.new_chat_member.status in ["left", "kicked"]:
        await context.bot.send_message(update.effective_chat.id, f"<b>{user.full_name}</b> {get_setting('leave_msg')}", parse_mode=ParseMode.HTML)

def main():
    init_db()
    # ফ্লাস্ক সার্ভার চালু করা (ব্যাকগ্রাউন্ডে)
    Thread(target=run_flask).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, input_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, auto_react))
    
    print("বট সচল আছে...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
