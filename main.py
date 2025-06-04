import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp

DOWNLOAD_DIR = "downloads"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎥 Send me a YouTube link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["url"] = url
    buttons = [
        [InlineKeyboardButton("🎵 Audio", callback_data="audio"),
         InlineKeyboardButton("🎬 Video", callback_data="video")]
    ]
    await update.message.reply_text("Choose format:", reply_markup=InlineKeyboardMarkup(buttons))

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_type = query.data
    url = context.user_data.get("url")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    await query.edit_message_text("⏳ Downloading... Please wait.")

    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.{format_type}.mp4")

    ydl_opts = {
        'outtmpl': filename,
        'format': 'bestaudio' if format_type == "audio" else 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'quiet': True,
        'merge_output_format': 'mp4',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            await query.edit_message_text("❌ Failed to download. Invalid link?")
            return

    await query.edit_message_text("✅ Downloaded. Uploading...")

    with open(filename, 'rb') as f:
        if format_type == "audio":
            await query.message.reply_audio(f)
        else:
            await query.message.reply_video(f)

    os.remove(filename)

app = ApplicationBuilder().token("7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(download_callback))

app.run_polling()
