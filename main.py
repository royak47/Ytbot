import os
import subprocess
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters, CallbackQueryHandler

BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"

# Start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Welcome to Media Downloader Bot!\n\n📥 Send a YouTube, Instagram, Twitter or Terabox link.")

# Download handler
def handle_link(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    chat_id = update.message.chat_id

    # Check for YouTube separately
    if "youtu" in url:
        keyboard = [
            [InlineKeyboardButton("🔽 Best Quality", callback_data=f"yt|{url}")],
            [InlineKeyboardButton("🎵 MP3 (Audio)", callback_data=f"mp3|{url}")]
        ]
        update.message.reply_text("🎞 Select download type:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text("📥 Downloading...")
        download_and_send(url, chat_id, context)

# Button actions
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    action, url = query.data.split("|", 1)
    chat_id = query.message.chat_id

    if action == "yt":
        query.edit_message_text("📥 Downloading best quality video...")
        download_and_send(url, chat_id, context)
    elif action == "mp3":
        query.edit_message_text("🎵 Converting to MP3...")
        download_and_send(url, chat_id, context, audio_only=True)

# Main download function
def download_and_send(url, chat_id, context, audio_only=False):
    outname = "media.%(ext)s"
    options = ["-o", outname, url]

    if audio_only:
        options = ["-x", "--audio-format", "mp3"] + options

    try:
        subprocess.run(["yt-dlp"] + options, check=True)

        for f in os.listdir():
            if f.startswith("media."):
                with open(f, "rb") as media:
                    if f.endswith(".mp3"):
                        context.bot.send_audio(chat_id=chat_id, audio=media)
                    elif f.endswith((".mp4", ".mkv", ".webm")):
                        context.bot.send_video(chat_id=chat_id, video=media, supports_streaming=True)
                    else:
                        context.bot.send_document(chat_id=chat_id, document=media)
                os.remove(f)
                return

        context.bot.send_message(chat_id, "❌ Download failed: File not found.")
    except subprocess.CalledProcessError as e:
        context.bot.send_message(chat_id, f"❌ Error during download: {str(e)}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    dp.add_handler(CallbackQueryHandler(button_handler))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
