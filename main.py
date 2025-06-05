import os
import aiohttp
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters,
)
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
MAX_TELEGRAM_SIZE = 49 * 1024 * 1024  # ~49MB
YOUTUBE_SITES = ["youtube.com", "youtu.be"]
TWITTER_SITES = ["twitter.com", "x.com"]
INSTAGRAM_SITES = ["instagram.com", "www.instagram.com"]

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send a YouTube, Instagram, or Twitter link to download the video.")

# Handle incoming links
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏬ Starting download...")

    if any(site in url for site in YOUTUBE_SITES):
        await download_video(update, url, use_cookie=True)
    elif any(site in url for site in INSTAGRAM_SITES + TWITTER_SITES):
        await download_video(update, url)
    else:
        await update.message.reply_text("❌ Unsupported link. Please send a valid YouTube, Instagram, or Twitter link.")

# Main download function with progress
async def download_video(update: Update, url: str, use_cookie=False):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    progress_msg = await update.message.reply_text("📥 Preparing to download...")

    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get("_percent_str", "").strip()
            eta = d.get("eta", "??")
            text = f"⏳ Downloading: {percent} | ETA: {eta}s"
            asyncio.run_coroutine_threadsafe(progress_msg.edit_text(text), asyncio.get_event_loop())

    ydl_opts = {
        'progress_hooks': [progress_hook],
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'quiet': True,
        'merge_output_format': 'mp4'
    }

    if use_cookie:
        ydl_opts['cookiefile'] = 'cookies.txt'
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await progress_msg.edit_text("✅ Download complete. Sending file...")
        await send_file(update, filename)

    except Exception as e:
        await progress_msg.edit_text(f"❌ Download failed:\n{e}")

# Upload to Telegram or GoFile
async def send_file(update: Update, filepath: str):
    try:
        if os.path.getsize(filepath) < MAX_TELEGRAM_SIZE:
            with open(filepath, 'rb') as f:
                await update.message.reply_video(video=f)
        else:
            gofile_url = await upload_to_gofile(filepath)
            if gofile_url:
                await update.message.reply_text(f"📤 File too large for Telegram. Here's your GoFile link:\n{gofile_url}")
            else:
                await update.message.reply_text("❌ Upload failed.")
    except Exception:
        await update.message.reply_text("❌ Error sending file.")
    finally:
        os.remove(filepath)

# Upload to GoFile API
async def upload_to_gofile(filepath: str):
    try:
        async with aiohttp.ClientSession() as session:
            # Step 1: Get the best server
            async with session.get("https://api.gofile.io/getServer") as r:
                server = (await r.json())["data"]["server"]

            # Step 2: Upload file
            with open(filepath, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=os.path.basename(filepath))
                async with session.post(f"https://{server}.gofile.io/uploadFile", data=data) as upload_resp:
                    result = await upload_resp.json()
                    return result["data"]["downloadPage"]
    except Exception:
        return None

# Run bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("🤖 Bot is running...")
    app.run_polling()
