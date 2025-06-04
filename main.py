import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
YOUTUBE_SITES = ['youtube.com', 'youtu.be']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send any video link from YouTube, Instagram, Twitter (X), or Terabox.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data['url'] = url

    await update.message.reply_text("⏬ Downloading... Please wait.")
    await direct_download(update, url)

async def list_youtube_formats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚠️ Format selection is disabled. Download will start automatically.")

async def download_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚠️ Format selection is disabled. Download will start automatically.")

async def direct_download(update: Update, url: str):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.mp4")
    opts = {
        'quiet': True,
        'outtmpl': filename,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'cookiefile': 'cookies.txt'  # 🔐 Use your browser cookies
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        with open(filename, 'rb') as f:
            await update.message.reply_video(f)
    except Exception as e:
        await update.message.reply_text(f"❌ Download failed: {e}")
    if os.path.exists(filename):
        os.remove(filename)

# Run the bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(list_youtube_formats, pattern="^list_youtube$"))
app.add_handler(CallbackQueryHandler(download_format, pattern="^(yt_dl:|back)$"))

print("✅ Bot is running...")
app.run_polling()
