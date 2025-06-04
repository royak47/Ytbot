#!/data/data/com.termux/files/usr/bin/bash

echo "🎥 YouTube Video Downloader using yt-dlp"
read -p "📎 Enter YouTube video URL: " url

if [[ -z "$url" ]]; then
    echo "❌ No URL entered. Exiting."
    exit 1
fi

echo "🔍 Fetching available formats..."
yt-dlp -F "$url"

echo
read -p "🎯 Enter format code to download (example: 22 or 137+140): " format

if [[ -z "$format" ]]; then
    echo "❌ No format selected. Exiting."
    exit 1
fi

echo "⬇️ Downloading..."
yt-dlp -f "$format" "$url"

echo "✅ Done!"
