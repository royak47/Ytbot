import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import pytz

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
DOWNLOAD_DIR = "downloads"

YOUTUBE_SITES = ['youtube.com', 'youtu.be']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send any video link from YouTube, Instagram, Twitter (X), or Terabox.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data['url'] = url

    if any(site in url for site in YOUTUBE_SITES):
        buttons = [[
            InlineKeyboardButton("🎵 Audio", callback_data="audio"),
            InlineKeyboardButton("🎬 Video", callback_data="video")
        ]]
        await update.message.reply_text("Choose format:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("⏬ Downloading... Please wait.")
        await direct_download(update, url)

async def list_formats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get("url")
    fmt_type = query.data
    context.user_data['type'] = fmt_type

    await query.edit_message_text("🔍 Fetching formats...")

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])

        buttons = []
        seen = set()
        for f in formats:
            fid = f.get("format_id")
            ext = f.get("ext", "")
            height = f.get("height", 0)
            abr = f.get("abr", 0)
            vcodec = f.get("vcodec")

            if fmt_type == "audio" and vcodec == "none" and abr and abr >= 64:
                label = f"{int(abr)}kbps"
                if label not in seen:
                    seen.add(label)
                    buttons.append([InlineKeyboardButton(label, callback_data=f"download:{fid}")])

            elif fmt_type == "video" and vcodec != "none" and height and ext in ["mp4", "webm"]:
                if height not in seen:
                    seen.add(height)
                    label = f"{height}p"
                    buttons.append([InlineKeyboardButton(label, callback_data=f"download:{fid}")])

        if not buttons:
            await query.edit_message_text("❌ No formats found.")
            return

        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
        await query.edit_message_text("🎯 Choose quality:", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        await query.edit_message_text(f"❌ Error fetching formats: {e}")

async def download_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        buttons = [[
            InlineKeyboardButton("🎵 Audio", callback_data="audio"),
            InlineKeyboardButton("🎬 Video", callback_data="video")
        ]]
        await query.edit_message_text("Choose format:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    fid = data.split(":")[1]
    url = context.user_data.get("url")
    fmt_type = context.user_data.get("type")

    await query.edit_message_text("⏬ Downloading selected format...")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    filename = os.path.join(DOWNLOAD_DIR, f"{query.from_user.id}.{fid}.{ 'mp3' if fmt_type == 'audio' else 'mp4'}")

    ydl_opts = {
        'quiet': True,
        'outtmpl': filename,
        'format': f"{fid}+bestaudio/best" if fmt_type == "video" else fid,
        'merge_output_format': 'mp4' if fmt_type == 'video' else 'mp3',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if fmt_type == 'audio' else [],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {e}")
        return

    await query.edit_message_text("📤 Uploading...")

    try:
        with open(filename, 'rb') as f:
            if fmt_type == "audio":
                await query.message.reply_audio(f)
            else:
                await query.message.reply_video(f)
    except:
        await query.message.reply_text("❌ Upload failed. File too large?")

    os.remove(filename)

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

# Start app
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(list_formats, pattern="^(audio|video)$"))
app.add_handler(CallbackQueryHandler(download_format, pattern="^(download:|back)$"))

print("✅ Bot is running...")
app.run_polling()
