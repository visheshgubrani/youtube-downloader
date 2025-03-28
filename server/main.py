import io
import os
from pathlib import Path
import tempfile
from yt_dlp import YoutubeDL
from fastapi import FastAPI, Body, HTTPException, Query
from fastapi.responses import StreamingResponse 
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get('/download')
async def download_mp3(url: str = Query(..., title='url')):
  if not url:
    raise HTTPException(status_code=400, detail='Invalid YT URL')
  
  with tempfile.TemporaryDirectory() as tmp_dir:
    ydl_opts = {
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
      "outtmpl": f"{tmp_dir}/%(title)s.%(ext)s",  # Output template
    }

    try:
      with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    except Exception as e:
      raise HTTPException(status_code=500, detail=f'Download Failed: {str(e)}')
    
    # FInd the generated mp3 file
    mp3_files = list(Path(tmp_dir).glob('*.mp3'))
    if not mp3_files:
      raise HTTPException(status_code=500, detail='No MP3 found')
    
    mp3_path = mp3_files[0]
    filename = mp3_path.name

    with open(mp3_path, 'rb') as f:
      mp3_content = f.read()

    return StreamingResponse(
      io.BytesIO(mp3_content),
      media_type='audio/mpeg',
      headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )