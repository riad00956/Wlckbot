import logging
import sqlite3
import random
import os  # Render এর পোর্টের জন্য যুক্ত করা হয়েছে
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler, ChatMemberHandler
)
from telegram.constants import ParseMode

# লগিং
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8265396096:AAGX4icnhHHkuPwZIzRk8fKXyjn_jQer9ZI"
OWNER_ID = 7832264582

# --- ডেটাবেজ লজিক ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("welcome_msg", "আমাদের গ্রুপে আপনাকে স্বাগতম!")')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("leave_msg", "গ্রুপ থেকে বিদায় নিলেন। ভালো থাকবেন!")')
    cursor.execute('INSERT OR IGNORE INTO settings VALUES ("react_text", "খুব সুন্দর হয়েছে! 😍")')
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
        [InlineKeyboardButton("💬 React Text", callback_data="set_react_text")],
        [InlineKeyboardButton("🎭 Edit Emojis", callback_data="set_emojis")],
        [InlineKeyboardButton("📊 Stats", callback_data="view_stats"), InlineKeyboardButton("❌ Close", callback_data="close_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_to_main")]])

# --- হ্যান্ডলারস ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 বট সচল আছে! /admin লিখুন।")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🛠 **Admin Control Panel**", reply_markup=main_admin_kb(), parse_mode=ParseMode.MARKDOWN)

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_main":
        await query.edit_message_text("🛠 **Admin Control Panel**", reply_markup=main_admin_kb())
    
    elif query.data == "set_welcome":
        context.user_data['waiting_for'] = "welcome_msg"
        context.user_data['panel_id'] = query.message.message_id
        await query.edit_message_text("📝 **নতুন ওয়েলকাম মেসেজটি লিখুন:**\n(বট শুরুতে মেনশন দিয়ে দিবে)", reply_markup=back_kb())

    elif query.data == "set_leave":
        context.user_data['waiting_for'] = "leave_msg"
        context.user_data['panel_id'] = query.message.message_id
        await query.edit_message_text("🏃 **কেউ লিভ নিলে কী মেসেজ যাবে তা লিখুন:**\n(বট শুরুতে নাম দিয়ে দিবে)", reply_markup=back_kb())

    elif query.data == "set_react_text":
        context.user_data['waiting_for'] = "react_text"
        context.user_data['panel_id'] = query.message.message_id
        await query.edit_message_text("💬 **রিপ্লাই টেক্সট লিখুন:**", reply_markup=back_kb())

    elif query.data == "set_emojis":
        context.user_data['waiting_for'] = "emoji_list"
        context.user_data['panel_id'] = query.message.message_id
        await query.edit_message_text("🎭 **ইমোজিগুলো কমা দিয়ে লিখুন:**\n\nফরম্যাট: `😐, 💔, 🙋`", reply_markup=back_kb())

    elif query.data == "view_stats":
        emojis = get_setting("emoji_list")
        welcome = get_setting("welcome_msg")
        leave = get_setting("leave_msg")
        await query.edit_message_text(f"📊 **সেটিংস:**\n\n👋 Welcome: {welcome}\n🏃 Leave: {leave}\n🎭 Emojis: `{emojis}`", reply_markup=back_kb())
    
    elif query.data == "close_panel":
        await query.message.delete()

async def input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = context.user_data.get('waiting_for')
    if target:
        new_value = update.message.text
        set_setting(target, new_value)
        await update.message.delete()
        panel_id = context.user_data.get('panel_id')
        context.user_data['waiting_for'] = None
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=panel_id, 
                                          text="✅ **সফলভাবে আপডেট হয়েছে!**", reply_markup=main_admin_kb())

# --- অটো ফিচারসমূহ ---
async def auto_react(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = get_setting("react_text")
    await update.message.reply_text(text)
    
    emoji_str = get_setting("emoji_list")
    emoji_list = [e.strip() for e in emoji_str.split(',')]
    random_emoji = random.choice(emoji_list)
    
    try:
        await update.message.set_reaction(reaction=[ReactionTypeEmoji(emoji=random_emoji)])
    except Exception as e:
        logging.error(f"Reaction error: {e}")

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    user = result.new_chat_member.user
    mention = user.mention_html()

    if result.old_chat_member.status in ["left", "kicked", "both_left"] and result.new_chat_member.status == "member":
        db_msg = get_setting("welcome_msg")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{mention} {db_msg}", parse_mode=ParseMode.HTML)

    elif result.new_chat_member.status in ["left", "kicked"]:
        db_msg = get_setting("leave_msg")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"<b>{user.full_name}</b> {db_msg}", parse_mode=ParseMode.HTML)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # হ্যান্ডলারসমূহ
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, input_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, auto_react))
    
    # Render এর জন্য পোর্ট বাইন্ডিং (এটি ম্যান্ডেটরি)
    port = int(os.environ.get("PORT", 8000))
    print(f"বট চলছে পোর্ট {port}-এ...")
    
    # run_polling এ allowed_updates যুক্ত করা হয়েছে
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
