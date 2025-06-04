import os
import yt_dlp
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

DOWNLOAD_DIR = "downloads"

async def download_youtube_direct(update: Update, url: str):
    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
        }

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        try:
            with open(filename, 'rb') as f:
                await update.message.reply_video(f)
        except:
            await update.message.reply_text("❌ Upload failed. File may be too large for Telegram.")

        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"❌ Error downloading YouTube video:\n{str(e)}")


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

        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        filename = os.path.join(DOWNLOAD_DIR, f"{query.from_user.id}_{fid}.mp4")

        ydl_opts = {
            'quiet': True,
            'outtmpl': filename,
            'format': fid,
            'cookiefile': 'cookies.txt',
            'merge_output_format': 'mp4',
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
