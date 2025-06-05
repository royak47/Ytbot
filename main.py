import os
import requests
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
import asyncio

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

DOWNLOAD_DIR = "downloads"
YOUTUBE_SITES = ["youtube.com", "youtu.be"]
TWITTER_SITES = ["twitter.com", "x.com"]
INSTAGRAM_SITES = ["instagram.com", "www.instagram.com"]

progress_messages = {}  # user_id: message object

def format_progress_bar(percent):
    blocks = int(percent // 10)
    bar = "█" * blocks + "░" * (10 - blocks)
    return f"[{bar}] {percent:.1f}%"

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

        progress_msg = await update.message.reply_text("📥 Starting download...")
        user_id = update.effective_user.id
        progress_messages[user_id] = progress_msg

        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'progress_hooks': [create_hook(user_id, update, context)],
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

        progress_msg = await update.message.reply_text("📥 Starting download...")
        user_id = update.effective_user.id
        progress_messages[user_id] = progress_msg

        ydl_opts = {
            'quiet': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'progress_hooks': [create_hook(user_id, update, context)],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await send_video(update, filename)

    except Exception as e:
        await update.message.reply_text(f"❌ Download failed:\n{str(e)}")


def create_hook(user_id, update, context):
    async def hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)

            if total:
                percent = downloaded * 100 / total
                bar = format_progress_bar(percent)
                text = f"📥 Downloading...\n{bar}"

                msg = progress_messages.get(user_id)
                if msg:
                    try:
                        await msg.edit_text(text)
                    except:
                        pass

        elif d['status'] == 'finished':
            msg = progress_messages.get(user_id)
            if msg:
                try:
                    await msg.edit_text("✅ Download complete! Preparing file...")
                except:
                    pass

    return lambda d: asyncio.create_task(hook(d))


async def send_video(update: Update, filepath):
    try:
        with open(filepath, 'rb') as f:
            await update.message.reply_video(video=f)
    except Exception as e:
        # Telegram upload failed, try Gofile
        gofile_url = await upload_to_gofile(filepath)
        if gofile_url:
            await update.message.reply_text(f"📤 File too large, uploaded to Gofile:\n{gofile_url}")
        else:
            await update.message.reply_text("❌ Upload failed. File may be too large.")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


async def upload_to_gofile(file_path):
    try:
        server_res = requests.get("https://api.gofile.io/getServer").json()
        server = server_res["data"]["server"]
        with open(file_path, "rb") as f:
            upload = requests.post(
                f"https://{server}.gofile.io/uploadFile",
                files={"file": f}
            )
        result = upload.json()
        if result["status"] == "ok":
            return result["data"]["downloadPage"]
        return None
    except Exception as e:
        print(f"❌ Gofile upload error: {e}")
        return None


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("🤖 Bot is running...")
    app.run_polling()
