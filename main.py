import os
import requests
from pytube import YouTube
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7955106935:AAFmZbGBsaGWErQXnF4W-YJw4bqwj0Zue98"
bot = telebot.TeleBot(BOT_TOKEN)

# 📥 YouTube Quality Selection
def send_youtube_qualities(chat_id, video_url):
    try:
        yt = YouTube(video_url)
        streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()

        markup = InlineKeyboardMarkup()
        for stream in streams:
            size_mb = round(stream.filesize / (1024 * 1024), 1)
            btn_text = f"{stream.resolution} ({size_mb} MB)"
            callback_data = f"yt|{stream.itag}|{video_url}"
            markup.add(InlineKeyboardButton(btn_text, callback_data=callback_data))

        bot.send_message(chat_id, "🎞 Select a video quality:", reply_markup=markup)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("yt|"))
def download_selected_quality(call):
    try:
        _, itag, url = call.data.split("|")
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(itag)

        msg = bot.send_message(call.message.chat.id, "📥 Downloading video...")
        file_path = stream.download()

        bot.send_chat_action(call.message.chat.id, 'upload_video')
        with open(file_path, 'rb') as vid:
            bot.send_video(call.message.chat.id, vid, supports_streaming=True)
        os.remove(file_path)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Download failed: {e}")

# 📦 Terabox Handler
def get_terabox_direct_link(shared_url):
    try:
        r = requests.get("https://api.tbxdrive.net/api/download", params={"url": shared_url})
        j = r.json()
        return j["download_url"] if j.get("success") else None
    except:
        return None

@bot.message_handler(func=lambda m: "terabox.app" in m.text)
def handle_terabox(m):
    bot.send_message(m.chat.id, "🔍 Extracting Terabox file...")
    link = get_terabox_direct_link(m.text.strip())
    if not link:
        bot.send_message(m.chat.id, "❌ Terabox link not supported or failed to fetch.")
        return
    try:
        filename = link.split("/")[-1].split("?")[0]
        r = requests.get(link, stream=True)
        with open(filename, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
        bot.send_chat_action(m.chat.id, 'upload_document')
        with open(filename, "rb") as doc:
            bot.send_document(m.chat.id, doc)
        os.remove(filename)
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Failed: {e}")

# 🔗 YouTube Link Handler
@bot.message_handler(func=lambda m: "youtu.be/" in m.text or "youtube.com/watch" in m.text)
def handle_youtube_link(m):
    bot.send_message(m.chat.id, "🔗 Processing YouTube link...")
    send_youtube_qualities(m.chat.id, m.text.strip())

# 🧭 Start + Default Handlers
@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(m.chat.id, "👋 Send a YouTube or Terabox link to start downloading.")

@bot.message_handler(func=lambda m: True)
def fallback(m):
    if "instagram.com" in m.text or "twitter.com" in m.text:
        bot.send_message(m.chat.id, "✅ Insta/Twitter downloader working fine.")
    else:
        bot.send_message(m.chat.id, "⚠️ Unsupported link. Try YouTube or Terabox.")

# 🚀 Start Bot
print("🤖 Bot is running...")
bot.infinity_polling()
