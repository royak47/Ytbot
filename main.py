import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import yt_dlp

BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"
DOWNLOAD_DIR = "downloads"
URL_KEY = "url"
TYPE_KEY = "type"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔗 Send any YouTube, Instagram, or Twitter video link.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data[URL_KEY] = url
    buttons = [
        [InlineKeyboardButton("🎵 Audio", callback_data="audio"),
         InlineKeyboardButton("🎬 Video", callback_data="video")]
    ]
    await update.message.reply_text("Choose format type:", reply_markup=InlineKeyboardMarkup(buttons))

async def list_formats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    url = context.user_data.get(URL_KEY)
    format_type = query.data
    context.user_data[TYPE_KEY] = format_type

    ydl_opts = {'quiet': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])

        buttons = []
        for f in formats:
            fid = f.get("format_id")
            ext = f.get("ext", "")
            acodec = f.get("acodec")
            vcodec = f.get("vcodec")
            height = f.get("height", 0)
            abr = f.get("abr", 0)
            fps = f.get("fps", 0)

            if format_type == "audio":
                if vcodec == "none" and abr and abr >= 128:
                    label = f"{int(abr)}kbps"
                    buttons.append((abr, InlineKeyboardButton(label, callback_data=f"download:{fid}")))

            elif format_type == "video":
                if vcodec != "none" and height and ext in ["mp4", "webm"]:
                    label = f"{height}p"
                    if fps:
                        label += f" {int(fps)}fps"
                    buttons.append((height, InlineKeyboardButton(label, callback_data=f"download:{fid}")))

        if not buttons:
            await query.edit_message_text("❌ No matching formats found.")
            return

        buttons.sort(key=lambda x: -x[0])
        keyboard = [[btn] for _, btn in buttons]

        # Add back button
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])

        await query.edit_message_text("📥 Select quality:", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await query.edit_message_text("❌ Error: Could not extract formats.")

async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        buttons = [
            [InlineKeyboardButton("🎵 Audio", callback_data="audio"),
             InlineKeyboardButton("🎬 Video", callback_data="video")]
        ]
        await query.edit_message_text("Choose format type:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("download:"):
        format_id = data.split(":")[1]
        url = context.user_data.get(URL_KEY)
        format_type = context.user_data.get(TYPE_KEY)

        await query.edit_message_text("⏳ Downloading... Please wait.")

        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        filename = os.path.join(DOWNLOAD_DIR, f"{query.from_user.id}_{format_id}.{ 'mp3' if format_type == 'audio' else 'mp4'}")

        ydl_opts = {
            'outtmpl': filename,
            'format': f"{format_id}+bestaudio/best" if format_type == "video" else format_id,
            'quiet': True,
            'merge_output_format': 'mp4' if format_type == "video" else 'mp3',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }] if format_type == "audio" else [],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            await query.edit_message_text("❌ Download failed. Try another format.")
            return

        await query.edit_message_text("✅ Uploading...")

        try:
            with open(filename, 'rb') as f:
                if format_type == "audio":
                    await query.message.reply_audio(f)
                else:
                    await query.message.reply_video(f)
        except Exception as e:
            await query.message.reply_text("❌ Failed to upload file.")

        os.remove(filename)

# Bot setup
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(list_formats, pattern="^(audio|video)$"))
app.add_handler(CallbackQueryHandler(download_callback, pattern="^(download:|back)$"))

print("✅ Bot is running...")
app.run_polling()
