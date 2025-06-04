import os
from yt_dlp import YoutubeDL
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "downloads"
YOUTUBE_SITES = ['youtube.com', 'youtu.be']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Send any video link from YouTube, Instagram, Twitter (X), or Terabox.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ Please send a valid URL.")
        return

    context.user_data['url'] = url

    if any(site in url for site in ["youtube.com", "youtu.be"]):
        await update.message.reply_text("⏬ Downloading best quality YouTube video... Please wait.")
        await download_youtube_direct(update, url)
    else:
        await update.message.reply_text("⏬ Downloading... Please wait.")
        await direct_download(update, url)

async def download_youtube_direct(update: Update, url: str):
    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt',  # ensure this file is present
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',  # best mp4
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
        }

        os.makedirs("downloads", exist_ok=True)

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        await update.message.reply_video(video=open(filename, 'rb'))

        # Clean up
        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"❌ Error downloading YouTube video:\n{str(e)}")
        
async def handle_format_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get("url")
    selected_format_id = query.data.split(":")[1]

    await query.edit_message_text("⏬ Downloading selected format...")

    try:
        ydl_opts = {
            'format': selected_format_id,
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'cookiefile': 'cookies.txt',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.download([url])

        await query.edit_message_text("✅ Download complete!")
        # Or optionally send file here if size is small

    except Exception as e:
        await query.edit_message_text(f"❌ Download failed: {str(e)}")

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
            'format': fid,
            'cookiefile': 'cookies.txt'
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

# Run the bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(list_youtube_formats, pattern="^list_youtube$"))
app.add_handler(CallbackQueryHandler(download_format, pattern="^(yt_dl:|back)$"))

print("✅ Bot is running...")
app.run_polling()
