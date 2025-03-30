from fastapi.middleware.cors import CORSMiddleware
import zipfile
from pathlib import Path
import shutil
from yt_dlp import YoutubeDL
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import FileResponse
import logging
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import re 
import urllib.parse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

# Set up logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  handlers=[
    logging.FileHandler('downloader.log'),
  ]
)

# Disable watchfiles logger
logging.getLogger('watchfiles').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # For dev
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  expose_headers=['Content-Disposition']
)

DOWNLOADS_DIR = Path('./temp_downloads')
DOWNLOADS_DIR.mkdir(exist_ok=True)

executor = ThreadPoolExecutor(max_workers=5)

def clean_filename(filename: str) -> str: 
  cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)[:150]
  return cleaned.encode('ascii', errors='ignore').decode().strip()

@app.on_event('startup')
async def startup():
  redis_connection = redis.from_url('redis://localhost:6379')
  await FastAPILimiter.init(redis_connection)

@app.on_event('shutdown')
async def shutdown_event():
  # Clean up temp downloads dir
  if DOWNLOADS_DIR.exists():
    for file in DOWNLOADS_DIR.glob('*'):
      try:
        if file.is_dir():
          shutil.rmtree(file, ignore_errors=True)
        else:
          file.unlink()
      except Exception as e:
        logger.error(f"Error cleaning up file {file}: {e}")

  logger.info("Application shutdown, cleaned up temp files")


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

# func to execute download in a thread
def download_media(url, options):
  with YoutubeDL(options) as ydl:
    return ydl.extract_info(url, download=True)

# Backgroud task to clean up a file after it's been served
def remove_temp_dir(temp_dir_path: str):
  try:
    if os.path.exists(temp_dir_path):
      shutil.rmtree(temp_dir_path, ignore_errors=True)
      logger.info(f'Cleaned up tmep file: {temp_dir_path}')
  except Exception as e:
    logger.error(f'Error removing tmep file: {temp_dir_path}: {e}')

@app.get('/download', dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def download_single_mp3(url: str = Query(..., title='url'), background_tasks: BackgroundTasks = None):
  logger.info(f'Single download request received for url" {url}')
  if not url:
    raise HTTPException(status_code=400, detail='Invalid YT URL')
  
  download_id = f"{int(asyncio.get_event_loop().time() * 1000)}"
  temp_dir = DOWNLOADS_DIR / download_id
  temp_dir.mkdir(exist_ok=True)
  
  
  try:
    # Execute yt-dlp in a separate thread to not block the event loop
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(
      executor,
      download_media,
      url,
      get_ytdl_options(str(temp_dir))
    )
    if '_type' in info and info['_type'] == 'playlist':
        logger.warning(f'Playlist url sent to wrong endpoint')
        raise HTTPException(400, 'Use playlist endpoint')
      
    mp3_files = list(temp_dir.glob('*.mp3'))
    if not mp3_files:
      raise HTTPException(status_code=500, detail='No MP3 found')
    
    mp3_path = mp3_files[0]
    logger.info(f'Successfully download: {mp3_path.name}')

    safe_filename = clean_filename(mp3_path.name)
    encoded_filename = urllib.parse.quote(safe_filename)

  #  Schedule file cleanup after response is sent
    if background_tasks:
      background_tasks.add_task(remove_temp_dir, str(temp_dir))

    return FileResponse(
    path=mp3_path,
    media_type='audio/mpeg',
    filename=safe_filename,
    headers={
      "Content-Disposition": (
        f'attachment; filename="{safe_filename}"; '
        f'filename*=UTF-8\'\'{encoded_filename}'
      ) 
    }
  )
  except HTTPException:
    # Clean the temp dir
    shutil.rmtree(temp_dir, ignore_errors=True)
    raise
  except Exception as e:
    # Clean the temp dir
    shutil.rmtree(temp_dir, ignore_errors=True)
    logger.error(f"Single download failed: {str(e)}")
    raise HTTPException(status_code=500, detail=f'Download Failed: {str(e)}')

@app.get('/download/playlist', dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def download_playlist(url: str = Query(..., title='url'), background_tasks: BackgroundTasks = None):
  logger.info(f'Playlist download request received for url: {url}')

  # Create a unique temp dir
  download_id = f'{int(asyncio.get_event_loop().time() * 1000)}'
  temp_dir = DOWNLOADS_DIR / download_id
  temp_dir.mkdir(exist_ok=True)
  
  try:
    # Get the playlist info
    loop = asyncio.get_event_loop()

    info = await loop.run_in_executor(executor, lambda: YoutubeDL({'quiet': True}).extract_info(url, download=False))
    
    if 'entries' not in info:
      logger.warning(f'Non-Playlist URL sent to playlist endpoint: {url}')
      raise HTTPException(400, 'Use single endpoint for single videos')
            
    playlist_title = clean_filename(info.get('title', 'playlist'))
    max_tracks = 50
    num_tracks = len(info['entries'])
    logger.info(f'processing playlist: {playlist_title} with {num_tracks} tracks (max {max_tracks})')

    # Download the playlist
    await loop.run_in_executor(
      executor,
      download_media,
      url,
      get_ytdl_options(str(temp_dir))
    )

    # Create ZIP in mem
    zip_path = temp_dir / f'{playlist_title}.zip'
    mp3_files = list(temp_dir.glob('*.mp3'))


    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
      for idx, mp3_file in enumerate(mp3_files[:max_tracks]):
        zip_file.write(mp3_file, arcname=mp3_file.name)

    logger.info(f'Playlist {playlist_title} packaged with {len(mp3_files)} tracks')
    safe_filename = f'{playlist_title}.zip'
    encoded_filename = urllib.parse.quote(safe_filename)

    if background_tasks:
      background_tasks.add_task(remove_temp_dir, str(temp_dir))

    return FileResponse(
      path=zip_path,
      media_type='application/zip',
      filename=safe_filename,
      headers={
         "Content-Disposition": (
            f'attachment; filename="{safe_filename}"; '
            f'filename*=UTF-8\'\'{encoded_filename}'
          )
        }
    )
  except HTTPException:
    shutil.rmtree(temp_dir, ignore_errors=True)
    raise
  except Exception as e:
    shutil.rmtree(temp_dir, ignore_errors=True)
    logger.error(f'Playlist download failed: {str(e)}')
    raise HTTPException(500, f'Playlist download failed: {str(e)}')
    
@app.get('/status')
async def status():
  return {'status': 'running'}

 