import io
from fastapi.middleware.cors import CORSMiddleware
import zipfile
from pathlib import Path
import tempfile
from yt_dlp import YoutubeDL
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse 
import logging
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import re 
import urllib.parse


# Set up logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s = %(name)s - %(levelname)s - %(message)s',
  handlers=[
    logging.FileHandler('downloader.log'),
  ]
)

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # For development only
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  expose_headers=['Content-Disposition']
)

def clean_filename(filename: str) -> str: 
  cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)[:150]
  return cleaned.encode('ascii', errors='ignore').decode().strip()

@app.on_event('startup')
async def startup():
  redis_connection = redis.from_url('redis://localhost:6379')
  await FastAPILimiter.init(redis_connection)

# Download Configuraiton
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


@app.get('/download', dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def download_single_mp3(url: str = Query(..., title='url')):
  logger.info(f'Single download request received for url" {url}')
  if not url:
    raise HTTPException(status_code=400, detail='Invalid YT URL')
  
  with tempfile.TemporaryDirectory() as tmp_dir:
    try:
      with YoutubeDL(get_ytdl_options(tmp_dir)) as ydl:
        info = ydl.extract_info(url, download=True)
        if '_type' in info and info['_type'] == 'playlist':
          logger.warning(f'Playlist url sent to wrong endpoint')
          raise HTTPException(400, 'Use playlist endpoint')
        
      mp3_files = list(Path(tmp_dir).glob('*.mp3'))
      if not mp3_files:
        raise HTTPException(status_code=500, detail='No MP3 found')

      mp3_path = mp3_files[0]
      logger.info(f'Successfully download: {mp3_path.name}')

      safe_filename = clean_filename(mp3_path.name)
      encoded_filename = urllib.parse.quote(safe_filename)

      return StreamingResponse(
      open(mp3_path, 'rb'),
      media_type='audio/mpeg',
      headers={
        "Content-Disposition": (
          f'attachment; filename="{safe_filename}"; '
          f'filename*=YTF-8\'\'{encoded_filename}'
        ) 
      }
    )
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f"Single download failed: {str(e)}")
      raise HTTPException(status_code=500, detail=f'Download Failed: {str(e)}')

@app.get('/download/playlist', dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def download_playlist(url: str = Query(..., title='url')):
  logger.info(f'Playlist download request received for url: {url}')
  with tempfile.TemporaryDirectory() as tmp_dir:
    try:
      # Get the playlist info
      with YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' not in info:
          logger.warning(f'Non-Playlist URL send to playlist endpoint: {url}')
          raise HTTPException(400, 'use single endpoint')
        
        playlist_title = info.get('title', 'playlist').replace(' ', '_')
        max_tracks = 50
        logger.info(f'processing playlist: {playlist_title} with {len(info['entries'])} tracks')

      with YoutubeDL(get_ytdl_options(tmp_dir)) as ydl:
        ydl.download([url])

      # Create ZIP in mem
      zip_buffer = io.BytesIO()
      mp3_files = list(Path(tmp_dir).glob('*.mp3'))

      with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for idx, mp3_file in enumerate(mp3_files[:max_tracks]):
          zip_file.write(mp3_file, arcname=mp3_file.name)
          logger.debug(f'Added to ZIP: {mp3_file.name}')
      logger.info(f'Playlist {playlist_title} packaged with {len(mp3_files)} tracks')

      zip_buffer.seek(0)
      return StreamingResponse(
        zip_buffer,
        media_type='application/zip',
        headers={
          "Content-Disposition": f'attachment; filename="{playlist_title}.zip"'
        }
      )
    except HTTPException:
      raise
    except Exception as e:
      logger.error(f'Playlist download failed: {str(e)}')
      raise HTTPException(500, f'Playlist download failed: {str(e)}')

