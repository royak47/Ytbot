import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

DOWNLOAD_DIR = "downloads"
URL_KEY = "url"
TYPE_KEY = "format_type"

RESOLUTIONS = [360, 480, 720, 1080, 1440, 2160]
MIN_AUDIO_KBPS = 128

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🖇️ Send a YouTube / Insta / Twitter link to download.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data[URL_KEY] = url
    buttons = [
        [InlineKeyboardButton("🎵 MP3 Audio", callback_data="audio"),
         InlineKeyboardButton("🎬 Video", callback_data="video")]
    ]
    await update.message.reply_text("Choose format:", reply_markup=InlineKeyboardMarkup(buttons))

async def list_formats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    url = context.user_data.get(URL_KEY)
    format_type = query.data
    context.user_data[TYPE_KEY] = format_type

    ydl_opts = {'quiet': True, 'skip_download': True}
    buttons = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for f in info.get("formats", []):
                # 🎵 Audio
                if format_type == "audio" and f.get("vcodec") == "none":
                    abr = f.get("abr", 0)
                    if abr >= MIN_AUDIO_KBPS:
                        label = f"{abr}kbps MP3"
                        buttons.append((abr, InlineKeyboardButton(label, callback_data=f"download:{f['format_id']}")))

                # 🎬 Video
                elif format_type == "video" and f.get("vcodec") != "none":
                    height = f.get("height", 0)
                    if height in RESOLUTIONS and f.get("acodec") != "none":
                        label = f"{height}p MP4"
                        buttons.append((height, InlineKeyboardButton(label, callback_data=f"download:{f['format_id']}")))
    except Exception as e:
        await query.edit_message_text("❌ Failed to fetch formats.")
        return

    if not buttons:
        await query.edit_message_text("❌ No matching formats found.")
        return

    # sort & display
    buttons.sort(key=lambda x: -x[0])
    keyboard = [[b] for _, b in buttons[:20]]
    await query.edit_message_text("📥 Choose quality:", reply_markup=InlineKeyboardMarkup(keyboard))

async def download_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    format_id = query.data.split(":")[1]
    format_type = context.user_data.get(TYPE_KEY)
    url = context.user_data.get(URL_KEY)

    filename = os.path.join(DOWNLOAD_DIR, f"{update.effective_user.id}.{format_id}.{('mp3' if format_type == 'audio' else 'mp4')}")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    await query.edit_message_text("⏳ Downloading... Please wait.")

    ydl_opts = {
        'format': format_id,
        'outtmpl': filename,
        'quiet': True,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }] if format_type == "audio" else []
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        await query.edit_message_text("❌ Download failed.")
        return

    if not os.path.exists(filename) or os.path.getsize(filename) < 1024:
        await query.edit_message_text("❌ File not found or empty.")
        return

    await query.edit_message_text("✅ Uploading...")

    try:
        with open(filename, 'rb') as f:
            if format_type == "audio":
                await query.message.reply_audio(f)
            else:
                try:
                    await query.message.reply_video(f)
                except:
                    f.seek(0)
                    await query.message.reply_document(f, caption="🎬 Sent as file (too large).")
    except Exception as e:
        await query.edit_message_text("❌ Upload failed.")
    finally:
        os.remove(filename)

# 🔐 Replace this with your bot token
BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(list_formats, pattern="^(audio|video)$"))
app.add_handler(CallbackQueryHandler(download_selected, pattern="^download:.*$"))
app.run_polling()
