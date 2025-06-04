import os
import yt_dlp
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
DOWNLOAD_DIR = "downloads"
YOUTUBE_SITES = ['youtube.com', 'youtu.be']
TERABOX_KEYWORDS = ['terabox', '4funbox']

# 🔹 /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send any video link from YouTube, Instagram, Twitter (X), or Terabox.")

# 🔹 /uploadcookies command
async def upload_cookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📎 Please send the *cookies.txt* file now.", parse_mode='Markdown')

# 🔹 Handle uploaded cookies.txt
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if doc.file_name != "cookies.txt":
        await update.message.reply_text("❌ Please send a file named *cookies.txt* only.", parse_mode='Markdown')
        return

    await doc.get_file().download_to_drive("cookies.txt")
    await update.message.reply_text("✅ cookies.txt has been updated successfully.")

# 🔹 Handle link messages
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    await update.message.reply_text("⏬ Downloading... Please wait.")

    if any(k in url for k in TERABOX_KEYWORDS):
        await download_terabox(update, url)
    else:
        await direct_download(update, url)

# 🔹 Direct video download using yt-dlp
async def direct_download(update: Update, url: str):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.mp4")
    opts = {
        'quiet': True,
        'outtmpl': filename,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4'
    }

    if any(site in url for site in YOUTUBE_SITES) and os.path.exists("cookies.txt"):
        opts['cookiefile'] = "cookies.txt"

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

# 🔹 Terabox special download (without aria2)
async def download_terabox(update: Update, url: str):
    try:
        info = yt_dlp.YoutubeDL({'quiet': True}).extract_info(url, download=False)
        direct_url = info.get("url", None)
        if not direct_url:
            raise Exception("Couldn't extract direct URL")

        filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}_terabox.mp4")
        r = requests.get(direct_url, stream=True)
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        with open(filename, 'rb') as f:
            await update.message.reply_document(f)
    except Exception as e:
        await update.message.reply_text(f"❌ Terabox download failed: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# 🔹 Bot Setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("uploadcookies", upload_cookies))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

print("✅ Bot is running...")
app.run_polling()
