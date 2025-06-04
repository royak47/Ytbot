import os
import yt_dlp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
COOKIES_FILE = "cookies.txt"  # Must be in the same directory

YOUTUBE_DOMAINS = ['youtube.com', 'youtu.be']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send any video link from YouTube, Instagram, Twitter (X), or Terabox.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("❌ Invalid link.")
        return

    await update.message.reply_text("⏬ Downloading... Please wait.")
    await download_video(update, url)

async def download_video(update: Update, url: str):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.mp4")

    opts = {
        'quiet': True,
        'outtmpl': filename,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        with open(filename, 'rb') as f:
            await update.message.reply_video(f)

    except Exception as e:
        await update.message.reply_text(f"❌ Download failed: {e}")

    finally:
        if os.path.exists(filename):
            os.remove(filename)

# Start bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

print("✅ Bot is running...")
app.run_polling()
