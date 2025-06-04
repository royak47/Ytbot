import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

DOWNLOAD_DIR = "downloads"
URL_KEY = "url"
TYPE_KEY = "format_type"
YT_FORMATS_KEY = "available_formats"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🖇️ Send a YouTube / Instagram / Twitter link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data[URL_KEY] = url
    buttons = [
        [InlineKeyboardButton("🎵 Audio (MP3)", callback_data="select_audio"),
         InlineKeyboardButton("🎬 Video", callback_data="select_video")]
    ]
    await update.message.reply_text("What do you want to download?", reply_markup=InlineKeyboardMarkup(buttons))

async def format_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_type = query.data.replace("select_", "")
    url = context.user_data.get(URL_KEY)
    context.user_data[TYPE_KEY] = format_type

    ydl_opts = {'quiet': True, 'skip_download': True, 'forcejson': True}
    formats = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for f in info['formats']:
                size = f.get('filesize', 0) or f.get('filesize_approx', 0)
                mb = f"{size//1024//1024}MB" if size else "?"

                # Audio (only MP3 > 128kbps)
                if format_type == "audio" and f.get("vcodec") == "none" and f.get('abr', 0) >= 128:
                    label = f"{f['format_id']} - {f['abr']}kbps - {f['ext']} - {mb}"
                    formats.append((f.get("abr", 0), InlineKeyboardButton(label, callback_data=f"download:{f['format_id']}")))

                # Video (sorted by resolution)
                elif format_type == "video" and f.get("vcodec") != "none" and f.get("height", 0) >= 360:
                    label = f"{f['format_id']} - {f.get('height')}p - {f['ext']} - {mb}"
                    formats.append((f.get("height", 0), InlineKeyboardButton(label, callback_data=f"download:{f['format_id']}")))
    except Exception as e:
        await query.edit_message_text("❌ Failed to extract formats.")
        return

    if not formats:
        await query.edit_message_text("❌ No suitable formats found.")
        return

    # sort by quality descending
    formats.sort(key=lambda x: -x[0])
    rows = [[btn] for _, btn in formats[:20]]  # limit to 20 buttons

    await query.edit_message_text("📥 Choose a quality:", reply_markup=InlineKeyboardMarkup(rows))
    context.user_data[YT_FORMATS_KEY] = formats

async def download_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_id = query.data.split(":")[1]

    url = context.user_data.get(URL_KEY)
    format_type = context.user_data.get(TYPE_KEY)
    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.{format_id}.{'mp3' if format_type == 'audio' else 'mp4'}")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    await query.edit_message_text("⏳ Downloading...")

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
        await query.edit_message_text("❌ Download failed.")
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

# 🔐 Add your real token here
BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(format_type_selected, pattern="select_.*"))
app.add_handler(CallbackQueryHandler(download_selected, pattern="download:.*"))
app.run_polling()
