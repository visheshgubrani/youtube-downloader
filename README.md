# YouTube to MP3 Downloader

This is a simple YouTube to MP3 downloader application built with **FastAPI** for the backend and **Vite + React** for the frontend.

## Features

- **Single MP3 Download**: Download a single YouTube video as an MP3 file.
- **Playlist Download**: Download all videos in a YouTube playlist as MP3 files.
- **Rate Limiting**: Prevent abuse by limiting the number of requests per user using Redis.

## Requirements

- Python 3.8+
- Redis (for rate limiting)
- Node.js (for the frontend)

## Backend

The backend is built with **FastAPI** and uses **yt-dlp** for downloading and converting YouTube videos to MP3. It provides two endpoints:

1. `/download/single` - Download a single video as MP3.
2. `/download/playlist` - Download a playlist as MP3.

### Running the Backend

You can run the backend using:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

## Frontend

The frontend is located in the `client` folder and is built using **Vite** and **React**.

### Running the Frontend

```bash
# Navigate to the client folder
cd client

# Install dependencies
npm install

# Start the development server
npm run dev
```

## Folder Structure

```
/home/akira/youtube-downloader/
├── main.py          # FastAPI backend
├── requirements.txt # Backend dependencies
├── client/          # Frontend code (Vite + React)
└── README.md        # Documentation
```

## Notes

- Ensure Redis is running before starting the backend.
- Configure rate limiting and other settings in the `config` file.

Enjoy downloading your favorite YouTube content as MP3!
