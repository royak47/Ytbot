import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp

DOWNLOAD_DIR = "downloads"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎥 Send me a YouTube link to download.")

# Handle incoming YouTube link and show quality options
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["url"] = url

    # Use yt_dlp to get available formats
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
                # Only combined formats (video+audio)
                if f.get("vcodec") != "none" and f.get("acodec") != "none":
                    label = f"{f['format_id']} - {f['format_note']} - {f['ext']} - {f['filesize']//1024//1024 if f.get('filesize') else 'unknown'}MB"
                    formats.append(InlineKeyboardButton(label, callback_data=f"video:{f['format_id']}"))
    except Exception as e:
        await update.message.reply_text("❌ Invalid YouTube link.")
        return

    if not formats:
        await update.message.reply_text("❌ No suitable formats found.")
        return

    context.user_data["formats"] = formats

    # Send top 10 buttons
    rows = [[btn] for btn in formats[:10]]
    await update.message.reply_text("🎞️ Choose quality:", reply_markup=InlineKeyboardMarkup(rows))

# Handle format selection and download the video
async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    url = context.user_data.get("url")

    if ":" in data:
        format_type, format_id = data.split(":")
    else:
        await query.edit_message_text("❌ Unknown format selected.")
        return

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.mp4")

    await query.edit_message_text("⏳ Downloading... Please wait.")

    ydl_opts = {
        'outtmpl': filename,
        'format': format_id,
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")
        return

    await query.edit_message_text("✅ Download complete. Uploading...")

    try:
        with open(filename, 'rb') as f:
            await query.message.reply_video(f)
        os.remove(filename)
    except Exception as e:
        await query.edit_message_text("✅ Downloaded but failed to send file.")

# ✅ INSERT YOUR BOT TOKEN HERE
BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(download_callback))

app.run_polling()
