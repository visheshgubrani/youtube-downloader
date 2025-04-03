import sys
import asyncio
import zipfile
import shutil
import urllib.parse
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks, APIRouter
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from .config import DOWNLOAD_DIR, RATE_LIMIT_SECONDS, RATE_LIMIT_TIMES, MAX_PLAYLIST_TRACKS, REDIS_URL
from .utils import clean_filename, remove_temp_dir
from .downloader import download_media, get_ytdl_options, get_playlist_info, executor

# Set up logger
import logging
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
  # Startup
  redis_connection = redis.from_url(REDIS_URL)
  await FastAPILimiter.init(redis_connection)
  logger.info('Application started, initialized rate limiter')

  yield

  # Shutdown Code
  await redis_connection.close()
  if DOWNLOAD_DIR.exists():
    for file in DOWNLOAD_DIR.glob('*'):
      try:
        if file.is_dir():
          shutil.rmtree(file, ignore_errors=True)
        else:
          file.unlink()
      except Exception as e:
        logger.error(f"Error cleaning up file {file}: {e}")

  logger.info('Application shutdown, cleaned up temp files')


app = FastAPI(
  title='YouTube to MP3 Downloader API',
  description='API for downloading YouTube videos and playlists as MP3s',
  version='0.1.0',
  lifespan=lifespan
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # For dev
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  expose_headers=['Content-Disposition']
)

# @app.on_event('startup')
# async def startup():
#   redis_connection = redis.from_url('redis://localhost:6379')
#   await FastAPILimiter.init(redis_connection)

# @app.on_event('shutdown')
# async def shutdown_event():
#   # Clean up temp downloads dir
#   if DOWNLOAD_DIR.exists():
#     for file in DOWNLOAD_DIR.glob('*'):
#       try:
#         if file.is_dir():
#           shutil.rmtree(file, ignore_errors=True)
#         else:
#           file.unlink()
#       except Exception as e:
#         logger.error(f"Error cleaning up file {file}: {e}")

#   logger.info("Application shutdown, cleaned up temp files")

endpoint_dependencies = []
if 'pytest' not in sys.modules:
  endpoint_dependencies.append(Depends(RateLimiter(times=RATE_LIMIT_TIMES, seconds=RATE_LIMIT_SECONDS)))

@app.get('/download', dependencies=endpoint_dependencies)
async def download_single_mp3(url: str = Query(..., title='url'), background_tasks: BackgroundTasks = None):
  logger.info(f'Single download request received for url" {url}')
  if not url:
    raise HTTPException(status_code=400, detail='Invalid YT URL')
  
  download_id = f"{int(asyncio.get_event_loop().time() * 1000)}"
  temp_dir = DOWNLOAD_DIR / download_id
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

@app.get('/download/playlist', dependencies=endpoint_dependencies)
async def download_playlist(url: str = Query(..., title='url'), background_tasks: BackgroundTasks = None):
  logger.info(f'Playlist download request received for url: {url}')

  # Create a unique temp dir
  download_id = f'{int(asyncio.get_event_loop().time() * 1000)}'
  temp_dir = DOWNLOAD_DIR / download_id
  temp_dir.mkdir(exist_ok=True)
  
  try:
    # Get the playlist info
    loop = asyncio.get_event_loop()

    info = await loop.run_in_executor(executor, lambda: get_playlist_info(url))
    
    if 'entries' not in info:
      logger.warning(f'Non-Playlist URL sent to playlist endpoint: {url}')
      raise HTTPException(400, 'Use single endpoint for single videos')
            
    playlist_title = clean_filename(info.get('title', 'playlist'))
    num_tracks = len(info['entries'])
    logger.info(f'processing playlist: {playlist_title} with {num_tracks} tracks (max {MAX_PLAYLIST_TRACKS})')

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
      for idx, mp3_file in enumerate(mp3_files[:MAX_PLAYLIST_TRACKS]):
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
