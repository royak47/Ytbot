import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
YOUTUBE_SITES = ["youtube.com", "youtu.be"]
TWITTER_SITES = ["twitter.com", "x.com"]
INSTAGRAM_SITES = ["instagram.com", "www.instagram.com"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube, Instagram, or Twitter link to download the video.")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏬ Downloading... Please wait.")

    if any(site in url for site in YOUTUBE_SITES):
        await download_youtube_direct(update, url)
    elif any(site in url for site in INSTAGRAM_SITES + TWITTER_SITES):
        await download_generic_video(update, url)
    else:
        await update.message.reply_text("❌ Unsupported link. Please send a YouTube, Instagram, or Twitter link.")


async def download_youtube_direct(update: Update, url: str):
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await send_video(update, filename)

    except Exception as e:
        await update.message.reply_text(f"❌ YouTube download failed:\n{str(e)}")


async def download_generic_video(update: Update, url: str):
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await send_video(update, filename)

    except Exception as e:
        await update.message.reply_text(f"❌ Download failed:\n{str(e)}")


async def send_video(update: Update, filepath):
    try:
        with open(filepath, 'rb') as f:
            await update.message.reply_video(video=f)
    except Exception as e:
        await update.message.reply_text("❌ Upload failed. File may be too large.")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("🤖 Bot is running...")
    app.run_polling()
