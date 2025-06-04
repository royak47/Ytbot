import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

DOWNLOAD_DIR = "downloads"
URL_KEY = "url"
TYPE_KEY = "format_type"
YT_FORMATS_KEY = "available_formats"

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔗 Send me a YouTube / Instagram / Twitter link to download.")

# When user sends a link
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data[URL_KEY] = url

    buttons = [
        [InlineKeyboardButton("🎵 Audio", callback_data="select_audio"),
         InlineKeyboardButton("🎬 Video", callback_data="select_video")]
    ]
    await update.message.reply_text("What do you want to download?", reply_markup=InlineKeyboardMarkup(buttons))

# When user selects audio/video
async def format_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_type = query.data.replace("select_", "")
    url = context.user_data.get(URL_KEY)
    context.user_data[TYPE_KEY] = format_type

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'forcejson': True
    }

    formats = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for f in info['formats']:
                if format_type == "audio" and f.get("vcodec") == "none":
                    size = f.get('filesize', 0) or f.get('filesize_approx', 0)
                    label = f"{f['format_id']} - {f['abr']}kbps - {f['ext']} - {size//1024//1024 if size else '?'}MB"
                    formats.append(InlineKeyboardButton(label, callback_data=f"download:{f['format_id']}"))

                elif format_type == "video" and f.get("vcodec") != "none":
                    size = f.get('filesize', 0) or f.get('filesize_approx', 0)
                    label = f"{f['format_id']} - {f.get('height', '?')}p - {f['ext']} - {size//1024//1024 if size else '?'}MB"
                    formats.append(InlineKeyboardButton(label, callback_data=f"download:{f['format_id']}"))
    except Exception as e:
        await query.edit_message_text("❌ Failed to extract formats. Invalid link or unsupported site.")
        return

    if not formats:
        await query.edit_message_text("❌ No suitable formats found.")
        return

    context.user_data[YT_FORMATS_KEY] = formats
    rows = [[btn] for btn in formats[:20]]  # Limit 20 buttons
    await query.edit_message_text("📥 Choose a quality:", reply_markup=InlineKeyboardMarkup(rows))

# Handle actual downloading
async def download_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_id = query.data.split(":")[1]

    url = context.user_data.get(URL_KEY)
    format_type = context.user_data.get(TYPE_KEY)
    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.{format_id}.{'mp3' if format_type == 'audio' else 'mp4'}")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    await query.edit_message_text("⏳ Downloading, please wait...")

    ydl_opts = {
        'format': format_id,
        'outtmpl': filename,
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }] if format_type == "audio" else []
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        await query.edit_message_text(f"❌ Download failed.")
        return

    await query.edit_message_text("✅ Uploading...")

    try:
        with open(filename, 'rb') as f:
            if format_type == "audio":
                await query.message.reply_audio(f)
            else:
                await query.message.reply_video(f)
    except:
        await query.edit_message_text("✅ Downloaded but failed to upload.")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# 🔐 BOT TOKEN
BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"

# Bot Setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(format_type_selected, pattern="select_.*"))
app.add_handler(CallbackQueryHandler(download_selected, pattern="download:.*"))

app.run_polling()
