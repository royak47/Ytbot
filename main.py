import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import subprocess
import os

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your Telegram Bot Token
TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! Send me any YouTube, Instagram, or Twitter link to download media.")

def clean_url(url):
    # Remove URL parameters & fix X.com -> twitter.com
    if "x.com" in url:
        url = url.replace("x.com", "twitter.com")
    if "?" in url:
        url = url.split("?")[0]
    return url

def download_media(url):
    filename = "media.%(ext)s"
    try:
        # Run yt-dlp subprocess
        subprocess.run(["yt-dlp", "-o", filename, clean_url(url)], check=True)
        # Find downloaded file
        for file in os.listdir("."):
            if file.startswith("media."):
                return file
    except subprocess.CalledProcessError as e:
        logger.error(f"Download error: {e}")
        return None

def handle_message(update: Update, context: CallbackContext):
    url = update.message.text.strip()
    update.message.reply_text("Downloading, please wait...")

    file_path = download_media(url)
    if file_path and os.path.exists(file_path):
        update.message.reply_document(document=open(file_path, 'rb'))
        os.remove(file_path)
    else:
        update.message.reply_text("❌ Sorry, failed to download from the provided link.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
