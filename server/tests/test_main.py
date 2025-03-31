import pytest 
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app 
from src.youtube_downloader.downloader import download_media, get_playlist_info

@pytest.fixture
def client():
  return TestClient(app)

@pytest.mark.asyncio
async def test_download_single_mp3(client):
  test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

  # Mock the download_media func
  with patch('src.youtube_downloader.downloader.download_media', new_callable=AsyncMock) as mock_download:
    mock_download.return_value = {'_type': 'video'}

    async with AsyncClient(base_url='http://test', transport=ASGITransport(app=app)) as async_client:
      response = await async_client.get(f'/download?url={test_url}')

  assert response.status_code == 200
  assert response.headers['content-type'] == 'audio/mpeg'

@pytest.mark.asyncio
async def test_download_playlist(client):
  test_url = 'https://www.youtube.com/playlist?list=PLrMc0dEL0Y_v3kd52_-YSjhNg76Qg-ZQH'

  # Mock get_playlist_info to return fake playlist data
  mock_playlist_info = {
    'title': 'Test Playlist',
    'entries': [{'id': 'vid1'}, {'id': 'vid2'}]
  }

  with patch('src.youtube_downloader.downloader.get_playlist_info', return_value=mock_playlist_info), \
       patch('src.youtube_downloader.downloader.download_media', new_callable=AsyncMock) as mock_download:
        
        mock_download.return_value = None

        async with AsyncClient(base_url='http://test', transport=ASGITransport(app=app)) as async_client:
           response = await async_client.get(f'/download/playlist?url={test_url}')
  
  assert response.status_code == 200
  assert response.headers['content-type'] == 'application/zip'