import re
import os 
import shutil
import logging 

logger = logging.getLogger(__name__)

def clean_filename(filename: str) -> str:
  cleaned = re.sub(r'[\\/*?:"<>|]', "", filename)[:150]
  return cleaned.encode('ascii', errors='ignore').decode().strip()

def remove_temp_dir(temp_dir_path: str):
  try:
    if os.path.exists(temp_dir_path):
      shutil.rmtree(temp_dir_path, ignore_errors=True)
      logger.info(f'Cleaned up temp dir: {temp_dir_path}')
  except Exception as e:
    logger.error(f'Error removing temp dir: {temp_dir_path}, {e}')

    