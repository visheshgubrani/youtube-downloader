import pytest
import shutil
import os
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import asyncio
from fastapi.testclient import TestClient
from fastapi import BackgroundTasks
import zipfile
import io

# Import your FastAPI app
from youtube_downloader.main import app, download_media, get_ytdl_options, clean_filename, remove_temp_dir, startup, shutdown_event

client = TestClient(app)

# Setup and teardown for tests
@pytest.fixture(autouse=True)
def setup_and_cleanup():
    # Setup test environment
    test_downloads_dir = Path('./test_downloads')
    test_downloads_dir.mkdir(exist_ok=True)
    
    # Patch the DOWNLOADS_DIR
    with patch('youtube_downloader.main.DOWNLOADS_DIR', test_downloads_dir):
        yield
    
    # Cleanup after tests
    if test_downloads_dir.exists():
        shutil.rmtree(test_downloads_dir)


@pytest.fixture
def mock_redis():
    with patch('youtube_downloader.main.redis.from_url') as mock:
        mock_redis_conn = MagicMock()
        mock.return_value = mock_redis_conn
        yield mock_redis_conn


@pytest.fixture
def mock_limiter():
    with patch('youtube_downloader.main.FastAPILimiter') as mock:
        yield mock


# Test utility functions
def test_clean_filename():
    # Test with special characters
    assert clean_filename('test/file\\*:?"<>|.mp3') == 'testfile.mp3'
    
    # Test with long filename
    long_name = 'a' * 200
    assert len(clean_filename(long_name)) <= 150
    
    # Test with non-ASCII characters
    assert clean_filename('tést fïlè.mp3') == 'tst fl.mp3'


def test_get_ytdl_options():
    options = get_ytdl_options('/test/path')
    
    assert options['format'] == 'bestaudio/best'
    assert len(options['postprocessors']) == 3
    assert options['outtmpl'] == '/test/path/%(title)s.%(ext)s'
    assert options['quiet'] is True


@pytest.mark.asyncio
async def test_startup(mock_redis, mock_limiter):
    await startup()
    mock_redis.assert_called_once_with('redis://localhost:6379')
    mock_limiter.init.assert_called_once()


@patch('youtube_downloader.main.logger')
@patch('youtube_downloader.main.DOWNLOADS_DIR')
@pytest.mark.asyncio
async def test_shutdown_event(mock_downloads_dir, mock_logger):
    # Setup mock files and directories
    mock_file1 = MagicMock()
    mock_file1.is_dir.return_value = False
    
    mock_file2 = MagicMock()
    mock_file2.is_dir.return_value = True
    
    mock_downloads_dir.exists.return_value = True
    mock_downloads_dir.glob.return_value = [mock_file1, mock_file2]
    
    # Call the function
    await shutdown_event()
    
    # Verify cleanup
    mock_file1.unlink.assert_called_once()
    assert not mock_file2.unlink.called
    shutil.rmtree.assert_called_once_with(mock_file2, ignore_errors=True)
    mock_logger.info.assert_called_once()


# Test the remove_temp_dir background task
@patch('youtube_downloader.main.logger')
@patch('os.path.exists')
@patch('shutil.rmtree')
def test_remove_temp_dir_success(mock_rmtree, mock_exists, mock_logger):
    mock_exists.return_value = True
    temp_dir = '/test/path'
    
    remove_temp_dir(temp_dir)
    
    mock_exists.assert_called_once_with(temp_dir)
    mock_rmtree.assert_called_once_with(temp_dir, ignore_errors=True)
    mock_logger.info.assert_called_once()


@patch('youtube_downloader.main.logger')
@patch('os.path.exists')
@patch('shutil.rmtree')
def test_remove_temp_dir_not_exists(mock_rmtree, mock_exists, mock_logger):
    mock_exists.return_value = False
    temp_dir = '/test/path'
    
    remove_temp_dir(temp_dir)
    
    mock_exists.assert_called_once_with(temp_dir)
    mock_rmtree.assert_not_called()
    mock_logger.info.assert_not_called()


@patch('youtube_downloader.main.logger')
@patch('os.path.exists')
@patch('shutil.rmtree')
def test_remove_temp_dir_exception(mock_rmtree, mock_exists, mock_logger):
    mock_exists.return_value = True
    mock_rmtree.side_effect = Exception("Test error")
    temp_dir = '/test/path'
    
    remove_temp_dir(temp_dir)
    
    mock_exists.assert_called_once_with(temp_dir)
    mock_rmtree.assert_called_once_with(temp_dir, ignore_errors=True)
    mock_logger.error.assert_called_once()


# Test download_media function
@patch('youtube_downloader.main.YoutubeDL')
def test_download_media(mock_ytdl):
    mock_ytdl_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance
    mock_ytdl_instance.extract_info.return_value = {'title': 'Test Video', 'ext': 'mp3'}
    
    url = 'https://www.youtube.com/watch?v=test'
    options = {'format': 'bestaudio'}
    
    result = download_media(url, options)
    
    mock_ytdl.assert_called_once_with(options)
    mock_ytdl_instance.extract_info.assert_called_once_with(url, download=True)
    assert result == {'title': 'Test Video', 'ext': 'mp3'}


# Test API endpoints
@patch('youtube_downloader.main.RateLimiter')
def test_status_endpoint(mock_rate_limiter):
    response = client.get('/status')
    assert response.status_code == 200
    assert response.json() == {'status': 'running'}


@patch('youtube_downloader.main.download_media')
@patch('youtube_downloader.main.asyncio.get_event_loop')
@patch('youtube_downloader.main.RateLimiter')
@pytest.mark.asyncio
async def test_download_single_mp3_success(mock_rate_limiter, mock_loop, mock_download_media):
    # Mock the event loop and download function
    mock_loop_instance = MagicMock()
    mock_loop.return_value = mock_loop_instance
    mock_loop_instance.time.return_value = 123.456
    
    # Set up the mock downloaded file
    test_mp3_path = Path('./test_downloads/123456/test_video.mp3')
    os.makedirs(test_mp3_path.parent, exist_ok=True)
    with open(test_mp3_path, 'wb') as f:
        f.write(b'test mp3 content')
    
    # Mock the executor run to return file info
    mock_info = {'title': 'Test Video', 'ext': 'mp3'}
    mock_loop_instance.run_in_executor.return_value = asyncio.Future()
    mock_loop_instance.run_in_executor.return_value.set_result(mock_info)
    
    # Create a test client with a mocked file response
    with patch('youtube_downloader.main.FileResponse', return_value=MagicMock()) as mock_file_response:
        response = client.get('/download?url=https://www.youtube.com/watch?v=test')
        
        # Verify the response
        assert mock_loop_instance.run_in_executor.called
        mock_file_response.assert_called_once()
        
        # Clean up the test file
        if test_mp3_path.exists():
            os.unlink(test_mp3_path)


@patch('youtube_downloader.main.download_media')
@patch('youtube_downloader.main.asyncio.get_event_loop')
@patch('youtube_downloader.main.RateLimiter')
@pytest.mark.asyncio
async def test_download_single_mp3_playlist_error(mock_rate_limiter, mock_loop, mock_download_media):
    # Mock the event loop and download function
    mock_loop_instance = MagicMock()
    mock_loop.return_value = mock_loop_instance
    mock_loop_instance.time.return_value = 123.456
    
    # Mock the executor run to return playlist info
    mock_info = {'_type': 'playlist', 'entries': [{'title': 'Video 1'}, {'title': 'Video 2'}]}
    mock_loop_instance.run_in_executor.return_value = asyncio.Future()
    mock_loop_instance.run_in_executor.return_value.set_result(mock_info)
    
    # Test with playlist URL sent to single download endpoint
    response = client.get('/download?url=https://www.youtube.com/playlist?list=test')
    
    assert response.status_code == 400
    assert 'Use playlist endpoint' in response.json()['detail']


@patch('youtube_downloader.main.YoutubeDL')
@patch('youtube_downloader.main.download_media')
@patch('youtube_downloader.main.asyncio.get_event_loop')
@patch('youtube_downloader.main.RateLimiter')
@pytest.mark.asyncio
async def test_download_playlist_success(mock_rate_limiter, mock_loop, mock_download_media, mock_ytdl):
    # Mock the event loop
    mock_loop_instance = MagicMock()
    mock_loop.return_value = mock_loop_instance
    mock_loop_instance.time.return_value = 123.456
    
    # Set up mock YoutubeDL instance
    mock_ytdl_instance = MagicMock()
    mock_ytdl.return_value = mock_ytdl_instance
    
    # Mock playlist info
    playlist_info = {
        'title': 'Test Playlist',
        'entries': [{'title': 'Video 1'}, {'title': 'Video 2'}]
    }
    mock_ytdl_instance.extract_info.return_value = playlist_info
    
    # Mock the download
    mock_loop_instance.run_in_executor.return_value = asyncio.Future()
    mock_loop_instance.run_in_executor.return_value.set_result(None)
    
    # Set up the mock mp3 files and zip
    test_dir = Path('./test_downloads/123456')
    os.makedirs(test_dir, exist_ok=True)
    
    test_mp3_1 = test_dir / 'video1.mp3'
    test_mp3_2 = test_dir / 'video2.mp3'
    with open(test_mp3_1, 'wb') as f:
        f.write(b'test mp3 content 1')
    with open(test_mp3_2, 'wb') as f:
        f.write(b'test mp3 content 2')
    
    # Mock zipfile creation
    with patch('zipfile.ZipFile'):
        # Mock file response
        with patch('youtube_downloader.main.FileResponse', return_value=MagicMock()) as mock_file_response:
            response = client.get('/download/playlist?url=https://www.youtube.com/playlist?list=test')
            
            # Verify the response
            mock_ytdl_instance.extract_info.assert_called_once()
            assert mock_loop_instance.run_in_executor.called
            mock_file_response.assert_called_once()
            
            # Clean up test files
            if test_mp3_1.exists():
                os.unlink(test_mp3_1)
            if test_mp3_2.exists():
                os.unlink(test_mp3_2)


@patch('youtube_downloader.main.YoutubeDL')
@patch('youtube_downloader.main.RateLimiter')
@pytest.mark.asyncio
async def test_download_playlist_not_playlist(mock_rate_limiter, mock_ytdl):
    # Mock YoutubeDL to return non-playlist info
    mock_ytdl_instance = MagicMock()
    mock_ytdl.return_value = mock_ytdl_instance
    
    # Single video info without 'entries'
    video_info = {'title': 'Single Video', 'id': 'test123'}
    mock_ytdl_instance.extract_info.return_value = video_info
    
    # Test with single video URL sent to playlist endpoint
    response = client.get('/download/playlist?url=https://www.youtube.com/watch?v=test')
    
    assert response.status_code == 400
    assert 'Use single endpoint for single videos' in response.json()['detail']


@patch('youtube_downloader.main.asyncio.get_event_loop')
@patch('youtube_downloader.main.RateLimiter')
@pytest.mark.asyncio
async def test_download_single_mp3_no_url(mock_rate_limiter, mock_loop):
    response = client.get('/download?url=')
    assert response.status_code == 400
    assert 'Invalid YT URL' in response.json()['detail']


@patch('youtube_downloader.main.download_media')
@patch('youtube_downloader.main.asyncio.get_event_loop')
@patch('youtube_downloader.main.RateLimiter')
@pytest.mark.asyncio
async def test_download_single_mp3_exception(mock_rate_limiter, mock_loop, mock_download_media):
    # Mock the event loop
    mock_loop_instance = MagicMock()
    mock_loop.return_value = mock_loop_instance
    mock_loop_instance.time.return_value = 123.456
    
    # Mock the executor run to raise an exception
    mock_loop_instance.run_in_executor.return_value = asyncio.Future()
    mock_loop_instance.run_in_executor.return_value.set_exception(Exception("Download failed"))
    
    # Test with error during download
    with patch('shutil.rmtree') as mock_rmtree:
        response = client.get('/download?url=https://www.youtube.com/watch?v=test')
        
        assert response.status_code == 500
        assert 'Download Failed' in response.json()['detail']
        mock_rmtree.assert_called_once()