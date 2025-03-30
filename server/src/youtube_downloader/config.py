from pathlib import Path
import os

BASE_DIR = Path(__file__).parent.parent.parent # Root Filder
LOGS_DIR = BASE_DIR / 'logs'
DOWNLOAD_DIR = BASE_DIR / 'temp_downloads'

LOGS_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Redis Config
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Rate limiting
RATE_LIMIT_TIMES = 5
RATE_LIMIT_SECONDS = 60 

# Download Settings 
MAX_PLAYLIST_TRACKS = 50
THREAD_POOL_SIZE = 5