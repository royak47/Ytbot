import os
import requests
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
YOUTUBE_SITES = ['youtube.com', 'youtu.be']

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send any video link from YouTube, Instagram, Twitter (X), or Terabox.")

# Handle message
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data['url'] = url

    if "terabox" in url or "teraboxshare.com" in url or "terabox.app" in url:
        await update.message.reply_text("🔍 Processing Terabox link...")
        await handle_terabox(update, url)
    elif any(site in url for site in YOUTUBE_SITES):
        await update.message.reply_text(
            "🔍 Getting YouTube formats...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Choose Quality", callback_data="list_youtube")]
            ])
        )
    else:
        await update.message.reply_text("⏬ Downloading... Please wait.")
        await direct_download(update, url)

# Fetch YouTube formats
async def list_youtube_formats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get("url")
    await query.edit_message_text("🔍 Fetching YouTube formats...")

    try:
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])

        buttons = []
        seen = set()
        for f in formats:
            fid = f.get("format_id")
            height = f.get("height")
            ext = f.get("ext")
            acodec = f.get("acodec")
            filesize = f.get("filesize") or 0

            if height and acodec != "none" and ext in ["mp4", "webm"]:
                label = f"{height}p ({round(filesize / 1024 / 1024)} MB)" if filesize else f"{height}p"
                if label not in seen:
                    seen.add(label)
                    buttons.append([InlineKeyboardButton(label, callback_data=f"yt_dl:{fid}")])

        if not buttons:
            await query.edit_message_text("❌ No downloadable formats found.")
            return

        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await query.edit_message_text("🎯 Choose quality:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

# Download selected YouTube format
async def download_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        await query.edit_message_text(
            "Choose format:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎬 Choose Quality", callback_data="list_youtube")]
            ])
        )
        return

    if data.startswith("yt_dl:"):
        fid = data.split(":")[1]
        url = context.user_data.get("url")

        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        filename = os.path.join(DOWNLOAD_DIR, f"{query.from_user.id}_{fid}.mp4")
        ydl_opts = {
            'quiet': True,
            'outtmpl': filename,
            'format': fid
        }

        await query.edit_message_text("⏬ Downloading...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            await query.edit_message_text(f"❌ Download failed: {e}")
            return

        await query.edit_message_text("📤 Uploading...")
        try:
            with open(filename, 'rb') as f:
                await query.message.reply_video(f)
        except:
            await query.message.reply_text("❌ Upload failed. File may be too large.")
        os.remove(filename)

# Direct download for non-YouTube
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

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        with open(filename, 'rb') as f:
            await update.message.reply_video(f)
    except Exception as e:
        await update.message.reply_text(f"❌ Download failed: {e}")
    if os.path.exists(filename):
        os.remove(filename)

# 🔥 Terabox handler using teradownloader.com
async def handle_terabox(update: Update, url: str):
    api_url = "https://teradownloader.com/api/grab"
    try:
        res = requests.get(api_url, params={"link": url}, headers={"User-Agent": "Mozilla/5.0"})
        data = res.json()

        if data.get("code") != 200 or not data.get("data"):
            await update.message.reply_text("❌ Failed to fetch file info from Terabox.")
            return

        files = data["data"].get("files") or data["data"].get("list")
        for file in files:
            name = file.get("filename")
            dlink = file.get("dlink")
            size = file.get("size")

            msg = f"📁 <b>{name}</b>\n📦 Size: {size}\n🔗 <a href='{dlink}'>Direct Download</a>"
            await update.message.reply_html(msg, disable_web_page_preview=True)

    except Exception as e:
        await update.message.reply_text(f"❌ Terabox error: {e}")

# Run the bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(list_youtube_formats, pattern="^list_youtube$"))
app.add_handler(CallbackQueryHandler(download_format, pattern="^(yt_dl:|back)$"))

print("✅ Bot is running...")
app.run_polling()
