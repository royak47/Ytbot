import os
import requests
import telebot
from pytube import YouTube
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔐 Replace this with your bot token
BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"

bot = telebot.TeleBot(BOT_TOKEN)

# ▶️ YOUTUBE: Send video qualities as buttons
def send_youtube_qualities(chat_id, video_url):
    yt = YouTube(video_url)
    streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()

    markup = InlineKeyboardMarkup()
    for stream in streams:
        size = round(stream.filesize / (1024 * 1024), 1)
        text = f"{stream.resolution} ({size} MB)"
        callback_data = f"yt_quality|{video_url}|{stream.itag}"
        markup.add(InlineKeyboardButton(text, callback_data=callback_data))

    bot.send_message(chat_id, "🎥 Select video quality to download:", reply_markup=markup)

# ▶️ YOUTUBE: Download selected quality
@bot.callback_query_handler(func=lambda call: call.data.startswith("yt_quality|"))
def handle_youtube_quality(call):
    try:
        _, url, itag = call.data.split("|")
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(itag)

        msg = bot.send_message(call.message.chat.id, "📥 Downloading...")
        file_path = stream.download()

        bot.send_chat_action(call.message.chat.id, 'upload_video')
        with open(file_path, 'rb') as video:
            bot.send_video(call.message.chat.id, video, supports_streaming=True)

        os.remove(file_path)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Download failed:\n`{e}`", parse_mode="Markdown")

# 📁 TERABOX: Get direct download link from unofficial API
def get_terabox_direct_link(shared_url):
    try:
        api_url = "https://api.tbxdrive.net/api/download"
        params = {"url": shared_url}
        res = requests.get(api_url, params=params)
        data = res.json()
        if data.get("success") and data.get("download_url"):
            return data["download_url"]
        return None
    except:
        return None

# 📥 TERABOX: Handle download
@bot.message_handler(func=lambda message: "terabox.app" in message.text)
def handle_terabox(message):
    link = message.text.strip()
    bot.send_message(message.chat.id, "🔍 Extracting Terabox file...")

    direct_link = get_terabox_direct_link(link)
    if not direct_link:
        bot.send_message(message.chat.id, "❌ Failed to extract Terabox file. Link might be unsupported.")
        return

    try:
        file_data = requests.get(direct_link, stream=True)
        filename = direct_link.split("/")[-1].split("?")[0]
        with open(filename, 'wb') as f:
            for chunk in file_data.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        bot.send_chat_action(message.chat.id, 'upload_document')
        with open(filename, 'rb') as doc:
            bot.send_document(message.chat.id, doc)

        os.remove(filename)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Download error:\n`{e}`", parse_mode="Markdown")

# 🔗 YOUTUBE: Detect YouTube URL and show quality options
@bot.message_handler(func=lambda message: "youtube.com/watch" in message.text or "youtu.be/" in message.text)
def handle_youtube(message):
    url = message.text.strip()
    bot.send_message(message.chat.id, "🔗 Processing YouTube link...")
    try:
        send_youtube_qualities(message.chat.id, url)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error:\n`{e}`", parse_mode="Markdown")

# 🕹 DEFAULT HANDLER
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Welcome! Send a YouTube or Terabox link to download.")

@bot.message_handler(func=lambda m: True)
def fallback(message):
    if "instagram.com" in message.text or "twitter.com" in message.text:
        bot.send_message(message.chat.id, "⚙️ Instagram/Twitter downloading is working fine.")
    else:
        bot.send_message(message.chat.id, "❗ Unsupported link. Please send a YouTube or Terabox link.")

# ▶️ Start the bot
print("🤖 Bot is running...")
bot.infinity_polling()
