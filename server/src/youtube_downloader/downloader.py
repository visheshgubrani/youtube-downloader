from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor
from . import config

# Thread pool executor
executor = ThreadPoolExecutor(max_workers=config.THREAD_POOL_SIZE)

def get_ytdl_options(output_dir: str):
  return {
    "format": "bestaudio/best",
    "postprocessors": [
        {  # Extract audio as MP3
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "0",  # Highest quality
        },
        {  # Add metadata
            "key": "FFmpegMetadata"
        },
        {  # Embed thumbnail
            "key": "EmbedThumbnail",
            "already_have_thumbnail": False
        }
      ],
      "writethumbnail": True,  # Write thumbnail to disk
      "outtmpl": f"{output_dir}/%(title)s.%(ext)s",  # Output template
      "quiet": True
  }

def download_media(url, options):
  with YoutubeDL(options) as ydl:
    return ydl.extract_info(url, download=True)
  
def get_playlist_info(url):
  with YoutubeDL({'quiet': True}) as ydl:
    return ydl.extract_info(url, download=False)
