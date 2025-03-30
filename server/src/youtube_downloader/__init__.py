import logging
from pathlib import Path 
from . import config

# Setup logging
logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  handlers=[
    logging.FileHandler(config.LOGS_DIR / 'downloader.log'),
  ]
)

# disable annoying watcher
logging.getLogger('watchfiles').setLevel(logging.ERROR)

__version__ = '0.1.0'
