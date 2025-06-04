#!/bin/bash

# Ask for video URL
read -p "🎥 Enter YouTube video URL: " url

# Validate URL
if [[ -z "$url" ]]; then
    echo "❌ No URL entered."
    exit 1
fi

# Use yt-dlp to download best video + audio and merge into MP4
yt-dlp -f "bv*+ba/best" --merge-output-format mp4 "$url"

echo "✅ Download complete!"
